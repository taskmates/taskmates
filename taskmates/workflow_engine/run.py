import asyncio
import contextlib
import contextvars
import importlib
from collections.abc import Mapping
from typing import Any, Dict, Optional, List, Union, Self, Iterator

import pytest
from blinker import Namespace, Signal
from opentelemetry import trace
from ordered_set import OrderedSet
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_serializer, field_validator
from typeguard import typechecked

from taskmates.core.coalesce import coalesce
from taskmates.lib.context_.temp_context import temp_context
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts
from taskmates.lib.opentelemetry_.format_span_name import format_span_name
from taskmates.lib.opentelemetry_.tracing import tracer
from taskmates.lib.str_.to_snake_case import to_snake_case
from taskmates.taskmates_runtime import TASKMATES_RUNTIME
from taskmates.workflow_engine.base_signals import BaseSignals
from taskmates.workflow_engine.daemon import Daemon
from taskmates.workflow_engine.default_environment_signals import default_environment_signals
from taskmates.workflow_engine.runner import Runner
from taskmates.workflows.contexts.run_context import RunContext, default_taskmates_dirs

Signal.set_class = OrderedSet


@typechecked
class ObjectiveKey(BaseModel, Mapping):
    model_config = ConfigDict(frozen=True)  # Make it immutable for hashing

    outcome: Optional[str] = None
    inputs: Dict[str, Any] = Field(default_factory=dict)  # Remove Optional, always return a dict
    requesting_run: Optional['Run'] = Field(default=None, exclude=True)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __iter__(self) -> Iterator[str]:
        return iter(['outcome', 'inputs', 'requesting_run'])

    def __len__(self) -> int:
        return 3

    def __hash__(self) -> int:
        return hash((self.outcome, str(self.inputs)))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ObjectiveKey):
            return NotImplemented
        return (self.outcome == other.outcome and
                self.inputs == other.inputs)


@typechecked
class Objective(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        # extra='allow',  # Allow extra fields that aren't serialized
        validate_assignment=True,
        from_attributes=True
    )

    key: ObjectiveKey
    runs: List[Any] = Field(default_factory=list, exclude=True)  # exclude from serialization
    result_future: Optional[asyncio.Future] = Field(default=None, exclude=True)
    sub_objectives: Dict[ObjectiveKey, 'Objective'] = Field(default_factory=dict, exclude=True)

    @property
    def outcome(self) -> Optional[str]:
        return self.key.outcome

    @property
    def inputs(self) -> Dict[str, Any]:
        return self.key.inputs

    @property
    def requesting_run(self) -> Optional['Run']:
        return self.key.requesting_run

    @model_validator(mode='before')
    @classmethod
    def convert_inputs(cls, data: Any) -> Any:
        if isinstance(data, dict) and 'inputs' in data and data['inputs'] is None:
            data['inputs'] = {}
        return data

    def get_or_create_sub_objective(self, outcome: str, args_key: Optional[Dict[str, Any]] = None) -> 'Objective':
        key = ObjectiveKey(outcome=outcome, inputs=args_key or {})
        if key not in self.sub_objectives:
            sub_objective = Objective(key=ObjectiveKey(outcome=outcome, inputs=self.key.inputs))
            sub_objective.result_future = asyncio.Future()
            self.sub_objectives[key] = sub_objective
        return self.sub_objectives[key]

    def set_future_result(self, outcome: str, args_key: Optional[Dict[str, Any]], result: Any) -> None:
        sub_objective = self.get_or_create_sub_objective(outcome, args_key)
        if not sub_objective.result_future.done():
            sub_objective.result_future.set_result(result)

    def get_future_result(self, outcome: str, args_key: Optional[Dict[str, Any]]) -> Any:
        sub_objective = self.get_or_create_sub_objective(outcome, args_key)
        if sub_objective.result_future.done():
            return sub_objective.result_future.result()
        return None

    @property
    def last_run(self):
        return self.runs[-1]

    def environment(self, context: RunContext):
        return Run(
            objective=self,
            context=context,
            daemons={},
            signals=default_environment_signals(),
            state={}
        )

    def attempt(self,
                context: Optional[RunContext] = None,
                daemons: Optional[Union[Dict[str, Daemon], List[Daemon]]] = None,
                state: Optional[Dict[str, Any]] = None,
                signals: Optional[Dict[str, Any]] = None
                ):
        if state is None:
            state = {}

        if signals is None:
            signals = {}

        context = coalesce(context, self.key.requesting_run.context)
        signals = {**self.key.requesting_run.signals, **signals}
        state = {**self.key.requesting_run.state, **state}

        return Run(
            objective=self,
            context=context,
            daemons=daemons,
            signals=signals,
            state=state
        )

    def execute(self):
        return Run(objective=self,
                   context=self.key.requesting_run.context,
                   daemons={},
                   signals=self.key.requesting_run.signals,
                   state=self.key.requesting_run.state)

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.key.outcome}>"


@typechecked
class Run(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra='allow'  # Allow extra fields that aren't serialized
    )

    objective: Objective
    context: RunContext = Field(default_factory=dict)
    signals: Dict[str, BaseSignals] = Field(default_factory=dict)
    state: Dict[str, Any] = Field(default_factory=dict)
    daemons: Dict[str, Daemon] = Field(default_factory=dict)

    # Runtime-only fields, excluded from serialization
    namespace: Namespace = Field(default_factory=Namespace, exclude=True)
    exit_stack: contextlib.ExitStack = Field(default_factory=contextlib.ExitStack, exclude=True)

    @model_validator(mode='before')  # type: ignore[no-untyped-decorator]
    @classmethod
    def convert_daemons(cls, data: Any) -> Any:
        if isinstance(data, dict) and 'daemons' in data and not isinstance(data['daemons'], dict):
            data['daemons'] = to_daemons_dict(data['daemons'])
        return data

    @field_serializer('signals')  # type: ignore[no-untyped-decorator]
    def serialize_signals(self, signals: Dict[str, BaseSignals]) -> Dict[str, List[str]]:
        """Serialize signals by storing their names"""
        return {
            group_name: list(signal_group.namespace.keys())
            for group_name, signal_group in signals.items()
            if isinstance(signal_group, BaseSignals)
        }

    @field_validator('signals', mode='before')  # type: ignore[no-untyped-decorator]
    @classmethod
    def deserialize_signals(cls, value: Any) -> Dict[str, BaseSignals]:
        """Reconstruct signals from their names"""
        if isinstance(value, dict) and all(isinstance(v, list) for v in value.values()):
            signals = {}
            for group_name, signal_list in value.items():
                signal_group = BaseSignals()
                for signal_name in signal_list:
                    signal_group.namespace[signal_name] = signal_group.namespace.signal(signal_name)
                signals[group_name] = signal_group
            return signals
        return value

    @field_serializer('daemons')  # type: ignore[no-untyped-decorator]
    def serialize_daemons(self, daemons: Dict[str, Daemon]) -> Dict[str, str]:
        """Serialize daemons by storing their class paths"""
        return {
            name: f"{daemon.__class__.__module__}.{daemon.__class__.__name__}"
            for name, daemon in daemons.items()
        }

    @field_validator('daemons', mode='before')  # type: ignore[misc, no-untyped-decorator]
    @classmethod
    def deserialize_daemons(cls, value: Any) -> Dict[str, Daemon]:
        """Reconstruct daemons from their class paths"""
        if isinstance(value, dict) and all(isinstance(v, str) for v in value.values()):
            daemons = {}
            for name, class_path in value.items():
                module_path, class_name = class_path.rsplit('.', 1)
                module = importlib.import_module(module_path)
                daemon_class = getattr(module, class_name)
                daemons[name] = daemon_class()
            return daemons
        return value

    def request(self, outcome: Optional[str] = None, inputs: Optional[Dict[str, Any]] = None) -> Objective:
        # TODO: add child objective to parent's sub_objectives
        return Objective(key=ObjectiveKey(
            outcome=outcome,
            inputs=inputs or {},  # Use empty dict if inputs is None
            requesting_run=self
        ))

    def __enter__(self) -> Self:
        TASKMATES_RUNTIME.get().initialize()

        # Sets the current execution context
        self.exit_stack.enter_context(temp_context(RUN, self))

        # Enters the context of all daemons
        self.exit_stack.enter_context(stacked_contexts(list(self.daemons.values())))

        return self

    def __exit__(self, exc_type: Optional[type], exc_val: Optional[Exception], exc_tb: Optional[Any]) -> None:
        self.exit_stack.close()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(outcome={self.objective.key.outcome})"

    async def run_steps(self, steps: Any) -> Any:
        self.objective.runs.append(self)

        runner = Runner(func=steps, inputs=self.objective.key.inputs)

        with tracer().start_as_current_span(
                format_span_name(steps, self.objective),
                kind=trace.SpanKind.INTERNAL
        ):
            with self:
                runner.start()
                return await runner.get_result()


def to_daemons_dict(jobs: Optional[Union[List[Daemon], Dict[str, Daemon], None]]) -> Dict[str, Daemon]:
    if jobs is None:
        return {}
    if isinstance(jobs, Run):
        return to_daemons_dict([jobs])
    if isinstance(jobs, dict):
        return jobs
    if isinstance(jobs, list):
        return {to_snake_case(job.__class__.__name__): job for job in jobs}
    raise ValueError(f"Invalid type {jobs!r}")


RUN: contextvars.ContextVar[Run] = contextvars.ContextVar(Run.__class__.__name__)


# Tests


class MockDaemon(Daemon):  # type: ignore[misc, type-arg]
    pass


class MockDaemon1(Daemon):  # type: ignore[misc, type-arg]
    pass


class MockDaemon2(Daemon):  # type: ignore[misc, type-arg]
    pass


@pytest.fixture
def test_context() -> RunContext:
    return RunContext(
        runner_config={
            "interactive": False,
            "format": "full",
            "taskmates_dirs": default_taskmates_dirs
        },
        runner_environment={
            "markdown_path": "test.md",
            "cwd": "/tmp"
        },
        run_opts={
            "model": "test",
            "max_steps": 10
        }
    )


def test_objective_key():
    # Test basic key creation
    key1 = ObjectiveKey(outcome="test", inputs={"key": "value"})
    key2 = ObjectiveKey(outcome="test", inputs={"key": "value"})
    key3 = ObjectiveKey(outcome="test", inputs={"key": "different"})

    # Test equality
    assert key1 == key2
    assert key1 != key3

    # Test hashing
    d = {key1: "value1", key3: "value3"}
    assert d[key2] == "value1"  # key2 should hash to the same value as key1

    # Test mapping interface
    assert key1["outcome"] == "test"
    assert key1["inputs"] == {"key": "value"}
    assert len(key1) == 3
    assert set(key1.keys()) == {"outcome", "inputs", "requesting_run"}


def test_objective_with_key():
    # Test that Objective properly uses ObjectiveKey
    key = ObjectiveKey(outcome="test", inputs={"key": "value"})
    obj = Objective(key=key)

    assert obj.key is key  # Should be the same instance
    assert obj.key.outcome == "test"
    assert obj.key.inputs == {"key": "value"}

    # Test sub_objectives with keys
    sub_key = ObjectiveKey(outcome="sub_test", inputs={"arg": "value"})
    sub_obj = obj.get_or_create_sub_objective(sub_key.outcome, sub_key.inputs)
    assert isinstance(sub_obj, Objective)

    # Test that the same key returns the same sub_objective
    sub_obj2 = obj.get_or_create_sub_objective(sub_key.outcome, sub_key.inputs)
    assert sub_obj2 is sub_obj


def test_run_serialization(context: RunContext) -> None:
    # Create a simple objective with ObjectiveKey
    key = ObjectiveKey(outcome="test_outcome", inputs={"key": "value"})
    objective = Objective(key=key)

    # Create signals
    signals = {"test_group": BaseSignals()}
    signals["test_group"].namespace.signal("test_signal")

    # Create a Run instance
    run: Run = Run(
        objective=objective,
        context=context,
        signals=signals,
        state={"state_key": "state_value"},
        daemons={"test_daemon": MockDaemon()}
    )

    # Serialize
    json_str = run.model_dump_json()

    # Deserialize
    deserialized_run = Run.model_validate_json(json_str)

    # Verify the deserialized run
    assert deserialized_run.objective.key == run.objective.key
    assert deserialized_run.state == run.state
    assert isinstance(list(deserialized_run.daemons.values())[0], MockDaemon)
    assert "test_signal" in list(deserialized_run.signals.values())[0].namespace


def test_run_serialization_with_complex_data(context: RunContext) -> None:
    key = ObjectiveKey(
        outcome="complex_test",
        inputs={
            "nested": {"a": 1, "b": [1, 2, 3]},
            "list": [1, "two", {"three": 3}]
        }
    )
    objective = Objective(key=key)

    run: Run = Run(
        objective=objective,
        context=context,
        signals={},
        state={"complex": {"nested": True}},
        daemons={}
    )

    json_str = run.model_dump_json()
    deserialized_run = Run.model_validate_json(json_str)

    assert deserialized_run.objective.key == run.objective.key
    assert deserialized_run.state == run.state


def test_run_serialization_with_multiple_daemons(context: RunContext) -> None:
    key = ObjectiveKey(outcome="multi_daemon_test")
    objective = Objective(key=key)

    run: Run = Run(
        objective=objective,
        context=context,
        signals={},
        state={},
        daemons={
            "daemon1": MockDaemon1(),
            "daemon2": MockDaemon2()
        }
    )

    json_str = run.model_dump_json()
    deserialized_run = Run.model_validate_json(json_str)

    assert isinstance(deserialized_run.daemons["daemon1"], MockDaemon1)
    assert isinstance(deserialized_run.daemons["daemon2"], MockDaemon2)


def test_run_serialization_with_multiple_signal_groups(context: RunContext) -> None:
    signals = {
        "group1": BaseSignals(),
        "group2": BaseSignals()
    }

    signals["group1"].namespace.signal("signal1")
    signals["group1"].namespace.signal("signal2")
    signals["group2"].namespace.signal("signal3")

    key = ObjectiveKey(outcome="multi_signal_test")
    objective = Objective(key=key)

    run: Run = Run(
        objective=objective,
        context=context,
        signals=signals,
        state={},
        daemons={}
    )

    json_str = run.model_dump_json()
    deserialized_run = Run.model_validate_json(json_str)

    assert "signal1" in deserialized_run.signals["group1"].namespace
    assert "signal2" in deserialized_run.signals["group1"].namespace
    assert "signal3" in deserialized_run.signals["group2"].namespace


def test_objective_initialization():
    # Test initialization with ObjectiveKey
    obj = Objective(key=ObjectiveKey(outcome="test", inputs={"key": "value"}))
    assert obj.key.outcome == "test"
    assert obj.key.inputs == {"key": "value"}
    assert obj.runs == []
    assert obj.key.requesting_run is None

    # Test with default values
    obj = Objective(key=ObjectiveKey())
    assert obj.key.outcome is None
    assert obj.key.inputs == {}
    assert obj.runs == []
    assert obj.key.requesting_run is None


async def test_objective_future_results():
    # Test basic future functionality
    key = ObjectiveKey(outcome="test")
    obj = Objective(key=key)

    # Test setting and getting a result
    obj.set_future_result("test_outcome", None, "test_result")
    result = obj.get_future_result("test_outcome", None)
    assert result == "test_result"

    # Test setting and getting a result with args_key
    args_key = {"args": (1, 2), "kwargs": {}}
    obj.set_future_result("test_outcome", args_key, "test_result_with_args")
    result = obj.get_future_result("test_outcome", args_key)
    assert result == "test_result_with_args"

    # Test getting non-existent result
    result = obj.get_future_result("non_existent", None)
    assert result is None

    # Test getting result with non-existent args_key
    result = obj.get_future_result("test_outcome", {"args": (3, 4), "kwargs": {}})
    assert result is None


async def test_run_future_results(test_context):
    # Test that Run's set_result and get_result properly use Objective's future system
    key = ObjectiveKey(outcome="test")
    run = Run(
        objective=Objective(key=key),
        context=test_context,
        signals={},
        state={},
        daemons={}
    )

    # Test setting and getting a result
    run.objective.set_future_result("test_outcome", None, "test_result")
    result = run.objective.get_future_result("test_outcome", None)
    assert result == "test_result"

    # Test setting and getting a result with args_key
    args_key = {"args": (1, 2), "kwargs": {}}
    run.objective.set_future_result("test_outcome", args_key, "test_result_with_args")
    result = run.objective.get_future_result("test_outcome", args_key)
    assert result == "test_result_with_args"

    # Test getting non-existent result
    result = run.objective.get_future_result("non_existent", None)
    assert result is None

    # Test getting result with non-existent args_key
    key = {"args": (3, 4), "kwargs": {}}
    result = run.objective.get_future_result("test_outcome", key)
    assert result is None


@pytest.mark.skip
async def test_objective_future_fallback():
    # Test that when a result is set without args_key, it's used as a fallback
    obj = Objective(key=ObjectiveKey(outcome="test"))

    # Set a result without args_key
    obj.set_future_result("test_outcome", None, "fallback_result")

    # Test that any args_key returns the fallback result when use_fallback is True
    result1 = obj.get_future_result("test_outcome", {"args": (1, 2), "kwargs": {}}, use_fallback=True)
    assert result1 == "fallback_result"

    result2 = obj.get_future_result("test_outcome", {"args": (3, 4), "kwargs": {}}, use_fallback=True)
    assert result2 == "fallback_result"

    # Test that setting a specific args_key overrides the fallback
    args_key = {"args": (1, 2), "kwargs": {}}
    obj.set_future_result("test_outcome", args_key, "specific_result")

    # The specific args_key should get its result
    result3 = obj.get_future_result("test_outcome", args_key)
    assert result3 == "specific_result"

    # Other args_keys should still get the fallback when use_fallback is True
    result4 = obj.get_future_result("test_outcome", {"args": (3, 4), "kwargs": {}}, use_fallback=True)
    assert result4 == "fallback_result"


@pytest.mark.skip
async def test_run_future_fallback(test_context):
    # Test that Run's result methods properly handle the fallback behavior
    run = Run(
        objective=Objective(key=ObjectiveKey(outcome="test")),
        context=test_context,
        signals={},
        state={},
        daemons={}
    )

    # Set a result without args_key
    run.objective.set_future_result("test_outcome", None, "fallback_result")

    # Test that any args_key returns the fallback result when use_fallback is True
    key = {"args": (1, 2), "kwargs": {}}
    result1 = run.objective.get_future_result("test_outcome", key, True)
    assert result1 == "fallback_result"

    key1 = {"args": (3, 4), "kwargs": {}}
    result2 = run.objective.get_future_result("test_outcome", key1, True)
    assert result2 == "fallback_result"

    # Test that setting a specific args_key overrides the fallback
    args_key = {"args": (1, 2), "kwargs": {}}
    run.objective.set_future_result("test_outcome", args_key, "specific_result")

    # The specific args_key should get its result
    result3 = run.objective.get_future_result("test_outcome", args_key, False)
    assert result3 == "specific_result"

    # Other args_keys should still get the fallback when use_fallback is True
    key2 = {"args": (3, 4), "kwargs": {}}
    result4 = run.objective.get_future_result("test_outcome", key2, True)
    assert result4 == "fallback_result"
