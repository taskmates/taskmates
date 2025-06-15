import asyncio
import contextvars
import importlib
from contextlib import AbstractContextManager, ExitStack
from typing import Any, Dict, Optional, List, Union, Self, TypeVar

import pytest
from blinker import Namespace, Signal
from opentelemetry import trace
from ordered_set import OrderedSet
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_serializer, field_validator
from typeguard import typechecked

from taskmates.core.workflow_engine.run_context import RunContext, default_taskmates_dirs
from taskmates.lib.context_.temp_context import temp_context
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts
from taskmates.lib.opentelemetry_.format_span_name import format_span_name
from taskmates.lib.str_.to_snake_case import to_snake_case
from taskmates.taskmates_runtime import TASKMATES_RUNTIME
from taskmates.core.workflow_engine.base_signals import BaseSignals
from taskmates.core.workflow_engine.composite_context_manager import CompositeContextManager
from taskmates.core.workflow_engine.default_environment_signals import default_environment_signals
from taskmates.core.workflow_engine.runner import Runner

Signal.set_class = OrderedSet

T = TypeVar('T')

tracer = trace.get_tracer_provider().get_tracer(__name__)


@typechecked
class ObjectiveKey(Dict[str, Any]):
    def __init__(self, outcome: Optional[str] = None,
                 inputs: Optional[Dict[str, Any]] = None,
                 requesting_run: Optional['Run'] = None) -> None:
        super().__init__()
        self['outcome'] = outcome
        self['inputs'] = inputs or {}  # args
        self['requesting_run'] = requesting_run  # context
        self._hash = hash((self['outcome'], str(self['inputs'])))

    def __hash__(self) -> int:
        return self._hash

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ObjectiveKey):
            return NotImplemented
        return (self['outcome'] == other['outcome'] and
                self['inputs'] == other['inputs'])


@typechecked
class Objective(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        from_attributes=True
    )

    of: Optional['Objective'] = None
    key: ObjectiveKey
    sub_objectives: Dict[ObjectiveKey, 'Objective'] = Field(default_factory=dict, exclude=True)
    result_future: asyncio.Future = Field(default_factory=asyncio.Future, exclude=True)
    runs: List[Any] = Field(default_factory=list, exclude=True)

    @field_validator('key', mode='before')
    @classmethod
    def validate_key(cls, value: Any) -> ObjectiveKey:
        if isinstance(value, dict):
            return ObjectiveKey(
                outcome=value.get('outcome'),
                inputs=value.get('inputs', {}),
                requesting_run=value.get('requesting_run')
            )
        return value

    @model_validator(mode='before')
    @classmethod
    def convert_inputs(cls, data: Any) -> Any:
        if isinstance(data, dict) and 'inputs' in data and data['inputs'] is None:
            data['inputs'] = {}
        return data

    def get_or_create_sub_objective(self, outcome: str,
                                    inputs: Optional[Dict[str, Any]] = None) -> 'Objective':
        key = ObjectiveKey(outcome=outcome, inputs=inputs or {})
        if key not in self.sub_objectives:
            sub_objective = Objective(of=self, key=ObjectiveKey(outcome=outcome, inputs=inputs or {}))
            self.sub_objectives[key] = sub_objective
        return self.sub_objectives[key]

    def set_future_result(self, outcome: str, inputs: Optional[Dict[str, Any]], result: Any) -> None:
        sub_objective = self.get_or_create_sub_objective(outcome, inputs)
        if not sub_objective.result_future.done():
            sub_objective.result_future.set_result(result)

    def get_future_result(self, outcome: str, inputs: Optional[Dict[str, Any]]) -> Any:
        sub_objective = self.get_or_create_sub_objective(outcome, inputs)
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

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.key['outcome']}>"

    def _get_root(self) -> 'Objective':
        current = self
        while current.of is not None:
            current = current.of
        return current

    def dump_graph(self, indent: str = "", current_objective: Optional['Objective'] = None) -> str:
        # Start with the current node
        status = ''
        if not self.result_future.done():
            status = ' CURRENT...' if self is current_objective else ' PENDING...'

        result = [
            f"{indent}└── {self.key['outcome'] or '<no outcome>'} {dict(self.key['inputs'])}{status}"]

        # Add all sub-objectives
        child_indent = indent + "    "
        for key, sub_obj in self.sub_objectives.items():
            result.append(sub_obj.dump_graph(child_indent, current_objective))

        return "\n".join(result)

    def print_graph(self) -> None:
        """
        Prints the entire objective hierarchy starting from the root.
        """
        root = self._get_root()
        print(root.dump_graph(current_objective=self))


@typechecked
class Run(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    objective: Objective
    context: RunContext = Field(default_factory=dict)

    signals: Dict[str, BaseSignals] = Field(default_factory=dict)
    state: Dict[str, Any] = Field(default_factory=dict)

    daemons: Dict[str, AbstractContextManager] = Field(default_factory=dict)

    # Runtime-only fields, excluded from serialization
    namespace: Namespace = Field(default_factory=Namespace, exclude=True)
    exit_stack: ExitStack = Field(default_factory=ExitStack, exclude=True)

    @model_validator(mode='before')
    @classmethod
    def convert_daemons(cls, data: Any) -> Any:
        if isinstance(data, dict) and 'daemons' in data and not isinstance(data['daemons'], dict):
            data['daemons'] = to_daemons_dict(data['daemons'])
        return data

    @field_serializer('signals')
    def serialize_signals(self, signals: Dict[str, BaseSignals]) -> Dict[str, List[str]]:
        """Serialize signals by storing their names"""
        return {
            group_name: list(signal_group.namespace.keys())
            for group_name, signal_group in signals.items()
            if isinstance(signal_group, BaseSignals)
        }

    @field_validator('signals', mode='before')
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

    @field_serializer('daemons')
    def serialize_daemons(self, daemons: Dict[str, AbstractContextManager]) -> Dict[str, str]:
        """Serialize daemons by storing their class paths"""
        return {
            name: f"{daemon.__class__.__module__}.{daemon.__class__.__name__}"
            for name, daemon in daemons.items()
        }

    @field_validator('daemons', mode='before')
    @classmethod
    def deserialize_daemons(cls, value: Any) -> Dict[str, AbstractContextManager]:
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

    def __enter__(self) -> Self:
        TASKMATES_RUNTIME.get().initialize()

        # Sets the current execution context
        self.exit_stack.enter_context(temp_context(RUN, self))

        # Enters the context of all daemons
        self.exit_stack.enter_context(stacked_contexts(list(self.daemons.values())))

        return self

    def __exit__(self, exc_type: Optional[type], exc_val: Optional[BaseException], exc_tb: Optional[Any]) -> None:
        self.exit_stack.close()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(outcome={self.objective.key['outcome']})"

    async def run_steps(self, steps: Any) -> Any:
        self.objective.runs.append(self)

        runner = Runner(func=steps, inputs=self.objective.key['inputs'])

        with tracer.start_as_current_span(
                format_span_name(steps, self.objective),
                kind=trace.SpanKind.INTERNAL
        ):
            with self:
                runner.start()
                return await runner.get_result()


def to_daemons_dict(jobs: Optional[Union[
    List[AbstractContextManager],
    Dict[str, AbstractContextManager], None]]) \
        -> Dict[str, AbstractContextManager]:
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


class MockDaemon(CompositeContextManager):  # type: ignore[misc, type-arg]
    pass


class MockDaemon1(CompositeContextManager):  # type: ignore[misc, type-arg]
    pass


class MockDaemon2(CompositeContextManager):  # type: ignore[misc, type-arg]
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

    # Test dictionary interface
    assert key1["outcome"] == "test"
    assert key1["inputs"] == {"key": "value"}
    assert len(key1) == 3
    assert set(key1.keys()) == {"outcome", "inputs", "requesting_run"}


def test_objective_with_key():
    # Test that Objective properly uses ObjectiveKey
    key = ObjectiveKey(outcome="test", inputs={"key": "value"})
    obj = Objective(key=key)

    # Test that the key values are preserved
    assert obj.key == key  # Check equality instead of identity
    assert obj.key['outcome'] == "test"
    assert obj.key['inputs'] == {"key": "value"}

    # Test sub_objectives with keys
    sub_key = ObjectiveKey(outcome="sub_test", inputs={"arg": "value"})
    sub_obj = obj.get_or_create_sub_objective(sub_key['outcome'], sub_key['inputs'])
    assert isinstance(sub_obj, Objective)

    # Test that the same key returns the same sub_objective
    sub_obj2 = obj.get_or_create_sub_objective(sub_key['outcome'], sub_key['inputs'])
    assert sub_obj2 is sub_obj  # This should still be the same instance


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
    assert obj.key['outcome'] == "test"
    assert obj.key['inputs'] == {"key": "value"}
    assert obj.runs == []
    assert obj.key['requesting_run'] is None

    # Test with default values
    obj = Objective(key=ObjectiveKey())
    assert obj.key['outcome'] is None
    assert obj.key['inputs'] == {}
    assert obj.runs == []
    assert obj.key['requesting_run'] is None


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


def test_objective_dump_graph():
    # Create a root objective
    root = Objective(key=ObjectiveKey(outcome="root", inputs={"root_input": "value"}))

    # Create some sub-objectives
    sub1 = root.get_or_create_sub_objective("child1", {"child1_input": "value1"})
    root.get_or_create_sub_objective("child2", {"child2_input": "value2"})

    # Create a sub-sub-objective
    sub1.get_or_create_sub_objective("grandchild1", {"grandchild1_input": "value3"})

    # Get the graph representation
    graph = root.dump_graph()

    # Verify the structure
    assert "root" in graph
    assert "child1" in graph
    assert "child2" in graph
    assert "grandchild1" in graph
    assert "{'root_input': 'value'}" in graph
    assert "{'child1_input': 'value1'}" in graph
    assert "{'child2_input': 'value2'}" in graph
    assert "{'grandchild1_input': 'value3'}" in graph

    # Verify indentation structure
    lines = graph.split("\n")
    assert lines[0].startswith("└──")  # Root level
    assert all(line.startswith("    ") for line in lines[1:])  # Indented children


def test_objective_get_root():
    # Create a chain of objectives
    root = Objective(key=ObjectiveKey(outcome="root"))
    child = Objective(key=ObjectiveKey(outcome="child"), of=root)
    grandchild = Objective(key=ObjectiveKey(outcome="grandchild"), of=child)

    # Test that _get_root returns the root objective from any level
    assert root._get_root() is root
    assert child._get_root() is root
    assert grandchild._get_root() is root

    # Test with a single objective (is its own root)
    single = Objective(key=ObjectiveKey(outcome="single"))
    assert single._get_root() is single


def test_objective_dump_graph_with_current():
    # Create a root objective
    root = Objective(key=ObjectiveKey(outcome="root", inputs={"root_input": "value"}))

    # Create some sub-objectives
    sub1 = root.get_or_create_sub_objective("child1", {"child1_input": "value1"})
    root.get_or_create_sub_objective("child2", {"child2_input": "value2"})

    # Create a sub-sub-objective
    sub1.get_or_create_sub_objective("grandchild1", {"grandchild1_input": "value3"})

    # Get the graph representation when called from sub1
    graph = root.dump_graph(current_objective=sub1)

    # Verify that sub1 shows as CURRENT and others show as PENDING
    assert "child1" in graph
    assert "CURRENT..." in graph
    assert "PENDING..." in graph
    assert graph.count("CURRENT...") == 1  # Only one objective should be marked as current
    assert graph.count("PENDING...") >= 1  # At least one objective should be marked as pending

    # Test that the structure is maintained
    lines = graph.split("\n")
    assert lines[0].startswith("└──")  # Root level
    assert all(line.startswith("    ") for line in lines[1:])  # Indented children
