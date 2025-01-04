import contextlib
import contextvars
import importlib
from typing import Any, Generic, TypeVar, Mapping, Dict, Optional, List, Union, Self

from blinker import Namespace, Signal
from opentelemetry import trace
from ordered_set import OrderedSet
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_serializer, field_validator
from typeguard import typechecked

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
from taskmates.workflows.contexts.context import Context

Signal.set_class = OrderedSet

TContext = TypeVar('TContext', bound=Mapping[str, Any])


@typechecked
class Objective(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra='allow'  # Allow extra fields that aren't serialized
    )

    outcome: Optional[str] = None
    inputs: Optional[Dict[str, Any]] = Field(default_factory=dict)
    requester: Optional['Run'] = Field(default=None, exclude=True)  # exclude from serialization
    runs: List[Any] = Field(default_factory=list, exclude=True)  # exclude from serialization

    @model_validator(mode='before')
    @classmethod
    def convert_inputs(cls, data: Any) -> Any:
        if isinstance(data, dict) and 'inputs' in data and data['inputs'] is None:
            data['inputs'] = {}
        return data

    @property
    def last_run(self):
        return self.runs[-1]

    def environment(self, context: Context):
        return Run(
            objective=self,
            context=context,
            daemons={},
            signals=default_environment_signals(),
            state={},
            results={}
        )

    def attempt(self,
                context: Optional[Context] = None,
                daemons: Optional[Union[Dict[str, Daemon], List[Daemon]]] = None,
                state: Optional[Dict[str, Any]] = None,
                signals: Optional[Dict[str, Any]] = None,
                results: Optional[Dict[str, Any]] = None
                ):
        if state is None:
            state = {}

        if signals is None:
            signals = {}

        context = self.requester.context
        signals = {**self.requester.signals, **signals}
        state = {**self.requester.state, **state}
        results = results or self.requester.results

        return Run(
            objective=self,
            context=context,
            daemons=daemons,
            signals=signals,
            state=state,
            results=results
        )

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.outcome}>"


@typechecked
class Run(BaseModel, Generic[TContext]):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra='allow'  # Allow extra fields that aren't serialized
    )

    objective: Objective
    context: TContext
    signals: Dict[str, BaseSignals] = Field(default_factory=dict)
    state: Dict[str, Any] = Field(default_factory=dict)
    results: Dict[str, Any] = Field(default_factory=dict)
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
        return Objective(outcome=outcome,
                         inputs=inputs,
                         requester=self)

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
        return f"{self.__class__.__name__}(outcome={self.objective.outcome})"

    def set_result(self, outcome: str, args_key: Optional[Dict[str, Any]], result: Any) -> None:
        if args_key is None:
            self.results[outcome] = result
        else:
            if outcome not in self.results:
                self.results[outcome] = {}
            self.results[outcome][str(args_key)] = result

    def get_result(self, outcome: str, args_key: Optional[Dict[str, Any]]) -> Any:
        if outcome not in self.results:
            return None

        if isinstance(self.results[outcome], dict):
            return self.results[outcome].get(str(args_key))

        return self.results[outcome]

    async def run_steps(self, steps: Any) -> Any:
        self.objective.runs.append(self)

        runner = Runner(func=steps, inputs=self.objective.inputs)

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


RUN: contextvars.ContextVar[Run[Any]] = contextvars.ContextVar(Run.__class__.__name__)


# Tests


class MockDaemon(Daemon):  # type: ignore[misc, type-arg]
    pass


class MockDaemon1(Daemon):  # type: ignore[misc, type-arg]
    pass


class MockDaemon2(Daemon):  # type: ignore[misc, type-arg]
    pass


def test_run_serialization() -> None:
    # Create a simple objective
    objective = Objective(outcome="test_outcome", inputs={"key": "value"})

    # Create a simple context
    context = Context()

    # Create signals
    signals = {"test_group": BaseSignals()}
    signals["test_group"].namespace.signal("test_signal")

    # Create a Run instance
    run: Run[Context] = Run(
        objective=objective,
        context=context,
        signals=signals,
        state={"state_key": "state_value"},
        results={"result_key": "result_value"},
        daemons={"test_daemon": MockDaemon()}
    )

    # Serialize
    json_str = run.model_dump_json()

    # Deserialize
    deserialized_run = Run.model_validate_json(json_str)

    # Verify the deserialized run
    assert deserialized_run.objective.outcome == run.objective.outcome
    assert deserialized_run.objective.inputs == run.objective.inputs
    assert deserialized_run.state == run.state
    assert deserialized_run.results == run.results
    assert isinstance(list(deserialized_run.daemons.values())[0], MockDaemon)
    assert "test_signal" in list(deserialized_run.signals.values())[0].namespace


def test_run_serialization_with_complex_data() -> None:
    objective = Objective(
        outcome="complex_test",
        inputs={
            "nested": {"a": 1, "b": [1, 2, 3]},
            "list": [1, "two", {"three": 3}]
        }
    )

    context = Context()

    run: Run[Context] = Run(
        objective=objective,
        context=context,
        signals={},
        state={"complex": {"nested": True}},
        results={"arrays": [[1, 2], [3, 4]]},
        daemons={}
    )

    json_str = run.model_dump_json()
    deserialized_run = Run.model_validate_json(json_str)

    assert deserialized_run.objective.inputs == run.objective.inputs
    assert deserialized_run.state == run.state
    assert deserialized_run.results == run.results


def test_run_serialization_with_multiple_daemons() -> None:
    objective = Objective(outcome="multi_daemon_test")
    context = Context()

    run: Run[Context] = Run(
        objective=objective,
        context=context,
        signals={},
        state={},
        results={},
        daemons={
            "daemon1": MockDaemon1(),
            "daemon2": MockDaemon2()
        }
    )

    json_str = run.model_dump_json()
    deserialized_run = Run.model_validate_json(json_str)

    assert isinstance(deserialized_run.daemons["daemon1"], MockDaemon1)
    assert isinstance(deserialized_run.daemons["daemon2"], MockDaemon2)


def test_run_serialization_with_multiple_signal_groups() -> None:
    signals = {
        "group1": BaseSignals(),
        "group2": BaseSignals()
    }

    signals["group1"].namespace.signal("signal1")
    signals["group1"].namespace.signal("signal2")
    signals["group2"].namespace.signal("signal3")

    objective = Objective(outcome="multi_signal_test")
    context = Context()

    run: Run[Context] = Run(
        objective=objective,
        context=context,
        signals=signals,
        state={},
        results={},
        daemons={}
    )

    json_str = run.model_dump_json()
    deserialized_run = Run.model_validate_json(json_str)

    assert "signal1" in deserialized_run.signals["group1"].namespace
    assert "signal2" in deserialized_run.signals["group1"].namespace
    assert "signal3" in deserialized_run.signals["group2"].namespace


def test_objective_initialization():
    # Test basic initialization
    obj = Objective(outcome="test", inputs={"key": "value"})
    assert obj.outcome == "test"
    assert obj.inputs == {"key": "value"}
    assert obj.runs == []
    assert obj.requester is None

    # Test with default values
    obj = Objective()
    assert obj.outcome is None
    assert obj.inputs == {}
    assert obj.runs == []
    assert obj.requester is None


def test_objective_serialization():
    # Create an objective with some data
    obj = Objective(
        outcome="test",
        inputs={"key": "value", "nested": {"a": 1, "b": [1, 2, 3]}}
    )

    # Serialize to JSON
    json_data = obj.model_dump_json()

    # Deserialize from JSON
    deserialized = Objective.model_validate_json(json_data)

    # Check values
    assert deserialized.outcome == obj.outcome
    assert deserialized.inputs == obj.inputs
    assert deserialized.runs == []
    assert deserialized.requester is None


def test_objective_with_complex_inputs():
    # Test with various types of inputs
    obj = Objective(
        outcome="complex",
        inputs={
            "string": "value",
            "number": 42,
            "list": [1, 2, 3],
            "dict": {"a": 1},
            "nested": {
                "list": [{"x": 1}, {"y": 2}],
                "dict": {"a": {"b": {"c": 3}}}
            }
        }
    )

    # Serialize and deserialize
    json_data = obj.model_dump_json()
    deserialized = Objective.model_validate_json(json_data)

    # Verify all complex data is preserved
    assert deserialized.inputs == obj.inputs


def test_objective_methods():
    from taskmates.workflows.contexts.context import Context
    from taskmates.types import RunOpts, RunnerConfig, RunnerEnvironment

    # Create an objective
    obj = Objective(outcome="test", inputs={"key": "value"})

    # Create a proper context with all required fields
    context = Context(
        run_opts=RunOpts(
            model="gpt-4",
            workflow="test",
            tools={},
            participants={},
            max_steps=10,
            jupyter_enabled=True
        ),
        runner_config=RunnerConfig(
            endpoint="test",
            interactive=False,
            format="full",
            output="test",
            taskmates_dirs=[]
        ),
        runner_environment=RunnerEnvironment(
            request_id="test",
            markdown_path="test",
            cwd="test",
            env={}
        )
    )

    # Test environment method
    env = obj.environment(context)
    assert env.objective == obj
    assert env.context == context
    assert env.daemons == {}
    assert env.state == {}
    assert env.results == {}
