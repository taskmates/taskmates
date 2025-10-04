import asyncio
import contextvars
from contextlib import AbstractContextManager, AbstractAsyncContextManager, ExitStack, contextmanager, \
    asynccontextmanager, AsyncExitStack
from typing import Any, Dict, List, Union, Self, TypeVar, Sequence, Optional
from typing import TypedDict

import pytest
from blinker import Signal
from opentelemetry import trace
from ordered_set import OrderedSet
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator
from typeguard import typechecked

from taskmates.core.workflow_engine.base_signals import BaseSignals
from taskmates.core.workflow_engine.composite_context_manager import CompositeContextManager
from taskmates.core.workflow_engine.run_context import RunContext
from taskmates.core.workflow_engine.runner import Runner
from taskmates.core.workflows.signals.control_signals import ControlSignals
from taskmates.core.workflows.signals.execution_environment_signals import ExecutionEnvironmentSignals
from taskmates.core.workflows.signals.input_streams_signals import InputStreamsSignals
from taskmates.core.workflows.signals.status_signals import StatusSignals
from taskmates.core.workflows.states.interrupt_state import InterruptState
from taskmates.defaults.settings import Settings
from taskmates.lib.context_.temp_context import temp_context
from taskmates.lib.contextlib_.stacked_contexts import ensure_async_context_manager
from taskmates.lib.opentelemetry_.format_span_name import format_span_name
from taskmates.lib.str_.to_snake_case import to_snake_case
from taskmates.taskmates_runtime import TASKMATES_RUNTIME
from taskmates.types import ResultFormat

Signal.set_class = OrderedSet

T = TypeVar('T')

tracer = trace.get_tracer_provider().get_tracer(__name__)


@typechecked
class ObjectiveKey(Dict[str, Any]):
    def __init__(self, outcome: Optional[str] = None,
                 inputs: Optional[Dict[str, Any]] = None,
                 requesting_run: Optional['Transaction'] = None) -> None:
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
    result_format: ResultFormat = {'format': 'completion', 'interactive': False}

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
        return Transaction(
            objective=self,
            context=context
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
class Transaction(BaseModel):
    class Emits(TypedDict):
        control: ControlSignals
        input_streams: InputStreamsSignals

    class Consumes(TypedDict):
        status: StatusSignals
        execution_environment: ExecutionEnvironmentSignals

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    objective: Objective

    context: RunContext = Field(default_factory=dict)

    emits: Dict[str, BaseSignals] = Field(default_factory=dict)
    consumes: Dict[str, BaseSignals] = Field(default_factory=dict)
    state: Dict[str, Any] = Field(default_factory=dict)
    resources: Dict[str, Any] = Field(default_factory=dict)

    def should_terminate(self) -> bool:
        """Check if the transaction should terminate."""
        return self.result_future.done() or self.interrupt_state.is_terminated()

    # daemons: Dict[str, AbstractContextManager] = Field(default_factory=dict)
    async_context_managers: Sequence[AbstractAsyncContextManager] = Field(default_factory=list)

    # Unified state management
    result_future: asyncio.Future = Field(default_factory=asyncio.Future, exclude=True)
    interrupt_state: 'InterruptState' = Field(default_factory=lambda: InterruptState(), exclude=True)

    # Runtime-only fields, excluded from serialization

    # namespace: Namespace = Field(default_factory=Namespace, exclude=True)

    exit_stack: ExitStack = Field(default_factory=ExitStack, exclude=True)
    async_exit_stack: AsyncExitStack = Field(default_factory=AsyncExitStack, exclude=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        outcome = self.objective.key['outcome']

        self.emits: Transaction.Emits = {
            'control': ControlSignals(name=outcome),
            'input_streams': InputStreamsSignals(name=outcome),
        }

        self.consumes: Transaction.Consumes = {
            'status': StatusSignals(name=outcome),
            'execution_environment': ExecutionEnvironmentSignals(name=outcome)
        }

        self.state = {}
        self.resources = {}

    @property
    def execution_context(self) -> Self:
        return self

    # @model_validator(mode='before')
    # @classmethod
    # def convert_daemons(cls, data: Any) -> Any:
    #     if isinstance(data, dict) and 'daemons' in data and not isinstance(data['daemons'], dict):
    #         data['daemons'] = to_daemons_dict(data['daemons'])
    #     return data
    #
    # @field_serializer('emits')
    # def serialize_emits(self, emits: Dict[str, BaseSignals]) -> Dict[str, List[str]]:
    #     """Serialize incoming signals by storing their names"""
    #     return {
    #         group_name: list(signal_group.namespace.keys())
    #         for group_name, signal_group in emits.items()
    #         if isinstance(signal_group, BaseSignals)
    #     }
    #
    # @field_serializer('consumes')
    # def serialize_consumes(self, consumes: Dict[str, BaseSignals]) -> Dict[str, List[str]]:
    #     """Serialize outgoing signals by storing their names"""
    #     return {
    #         group_name: list(signal_group.namespace.keys())
    #         for group_name, signal_group in consumes.items()
    #         if isinstance(signal_group, BaseSignals)
    #     }
    #
    # @field_validator('emits', mode='before')
    # @classmethod
    # def deserialize_emits(cls, value: Any) -> Dict[str, BaseSignals]:
    #     """Reconstruct incoming signals from their names"""
    #     if isinstance(value, dict) and all(isinstance(v, list) for v in value.values()):
    #         signals = {}
    #         for group_name, signal_list in value.items():
    #             signal_group = BaseSignals(name="BaseSignals")
    #             for signal_name in signal_list:
    #                 signal_group.namespace[signal_name] = signal_group.namespace.signal(signal_name)
    #             signals[group_name] = signal_group
    #         return signals
    #     return value
    #
    # @field_validator('consumes', mode='before')
    # @classmethod
    # def deserialize_consumes(cls, value: Any) -> Dict[str, BaseSignals]:
    #     """Reconstruct outgoing signals from their names"""
    #     if isinstance(value, dict) and all(isinstance(v, list) for v in value.values()):
    #         signals = {}
    #         for group_name, signal_list in value.items():
    #             signal_group = BaseSignals(name="BaseSignals")
    #             for signal_name in signal_list:
    #                 signal_group.namespace[signal_name] = signal_group.namespace.signal(signal_name)
    #             signals[group_name] = signal_group
    #         return signals
    #     return value
    #
    # @field_serializer('daemons')
    # def serialize_daemons(self, daemons: Dict[str, AbstractContextManager]) -> Dict[str, str]:
    #     """Serialize daemons by storing their class paths"""
    #     return {
    #         name: f"{daemon.__class__.__module__}.{daemon.__class__.__name__}"
    #         for name, daemon in daemons.items()
    #     }
    #
    # @field_validator('daemons', mode='before')
    # @classmethod
    # def deserialize_daemons(cls, value: Any) -> Dict[str, AbstractContextManager]:
    #     """Reconstruct daemons from their class paths"""
    #     if isinstance(value, dict) and all(isinstance(v, str) for v in value.values()):
    #         daemons = {}
    #         for name, class_path in value.items():
    #             module_path, class_name = class_path.rsplit('.', 1)
    #             module = importlib.import_module(module_path)
    #             daemon_class = getattr(module, class_name)
    #             daemons[name] = daemon_class()
    #         return daemons
    #     return value

    @contextmanager
    def transaction_context(self):
        TASKMATES_RUNTIME.get().initialize()

        # Sets the current execution context
        self.exit_stack.enter_context(temp_context(TRANSACTION, self))

        # TODO: this is what we want to get rid of
        # Enters the context of all daemons
        # self.exit_stack.enter_context(stacked_contexts(list(self.daemons.values())))

        try:
            yield self
        finally:
            self.exit_stack.close()

    @asynccontextmanager
    async def async_transaction_context(self):
        async with self.async_exit_stack:
            for cm in self.async_context_managers:
                await self.async_exit_stack.enter_async_context(cm)
            with self.transaction_context():
                yield self

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(outcome={self.objective.key['outcome']})"

    async def run_steps(self, steps: Any) -> Any:
        self.objective.runs.append(self)

        runner = Runner(func=steps, inputs=self.objective.key['inputs'])

        with tracer.start_as_current_span(
                format_span_name(steps, self.objective),
                kind=trace.SpanKind.INTERNAL
        ):
            async with self.async_transaction_context():
                runner.start()
                return await runner.get_result()

    def create_child_transaction(self,
                                 outcome: str,
                                 inputs: Optional[Dict[str, Any]] = None,
                                 transaction_class: Optional[type['Transaction']] = None,
                                 result_format=None) -> 'Transaction':
        from taskmates.core.workflows.markdown_completion.bound_contexts import bound_contexts

        # Use the provided class or default to Transaction
        if transaction_class is None:
            transaction_class = Transaction

        # Create the child objective linked to the parent
        child_objective = Objective(
            of=self.objective,
            key=ObjectiveKey(
                outcome=outcome,
                inputs=inputs or {},
                requesting_run=self,
            ),
            **({"result_format": result_format} if result_format else {})
        )

        # Create the child transaction
        child = transaction_class(objective=child_objective, context=self.context.copy())

        # Add bound_contexts to the child's async context managers
        bound_context_manager = ensure_async_context_manager(
            bound_contexts(self, child)
        )
        child.async_context_managers = list(child.async_context_managers) + [bound_context_manager]

        return child

    @classmethod
    def create(cls, inputs=None):
        if inputs is None:
            inputs = {}
        context = Settings().get()
        # context["runner_config"].update({
        #     "interactive": False,
        #     "format": "completion",
        # })
        return cls(
            objective=Objective(key=ObjectiveKey(
                outcome=cls.__name__,
                inputs=inputs
            )),
            context=context
        )


def to_daemons_dict(jobs: Optional[Union[
    List[AbstractContextManager],
    Dict[str, AbstractContextManager], None]]) \
        -> Dict[str, AbstractContextManager]:
    if jobs is None:
        return {}
    if isinstance(jobs, Transaction):
        return to_daemons_dict([jobs])
    if isinstance(jobs, dict):
        return jobs
    if isinstance(jobs, list):
        return {to_snake_case(job.__class__.__name__): job for job in jobs}
    raise ValueError(f"Invalid type {jobs!r}")


TRANSACTION: contextvars.ContextVar[Transaction] = contextvars.ContextVar(Transaction.__class__.__name__)


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
        runner_environment={
            "taskmates_dirs": [],
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


# def test_run_serialization(context: RunContext) -> None:
#     # Create a simple objective with ObjectiveKey
#     key = ObjectiveKey(outcome="test_outcome", inputs={"key": "value"})
#     objective = Objective(key=key)
#
#     # Create signals
#     emits = {"test_group": BaseSignals(name="BaseSignals")}
#     emits["test_group"].namespace.signal("test_signal")
#     consumes = {"test_group": BaseSignals(name="BaseSignals")}
#     consumes["test_group"].namespace.signal("test_signal")
#
#     # Create a Run instance
#     run: Transaction = Transaction(
#         objective=objective,
#         context=context,
#         emits=emits,
#         consumes=consumes,
#         state={"state_key": "state_value"},
#         daemons={"test_daemon": MockDaemon()}
#     )
#
#     # Serialize
#     json_str = run.model_dump_json()
#
#     # Deserialize
#     deserialized_run = Transaction.model_validate_json(json_str)
#
#     # Verify the deserialized run
#     assert deserialized_run.objective.key == run.objective.key
#     assert deserialized_run.execution_context.state == run.execution_context.state
#     assert isinstance(list(deserialized_run.daemons.values())[0], MockDaemon)
#     assert "test_signal" in list(deserialized_run.execution_context.emits.values())[0].namespace
#     assert "test_signal" in list(deserialized_run.execution_context.consumes.values())[0].namespace


# def test_run_serialization_with_complex_data(context: RunContext) -> None:
#     key = ObjectiveKey(
#         outcome="complex_test",
#         inputs={
#             "nested": {"a": 1, "b": [1, 2, 3]},
#             "list": [1, "two", {"three": 3}]
#         }
#     )
#     objective = Objective(key=key)
#
#     run: Transaction = Transaction(
#         objective=objective,
#         context=context,
#         emits={},
#         consumes={},
#         state={"complex": {"nested": True}},
#         daemons={}
#     )
#
#     json_str = run.model_dump_json()
#     deserialized_run = Transaction.model_validate_json(json_str)
#
#     assert deserialized_run.objective.key == run.objective.key
#     assert deserialized_run.execution_context.state == run.execution_context.state


# def test_run_serialization_with_multiple_daemons(context: RunContext) -> None:
#     key = ObjectiveKey(outcome="multi_daemon_test")
#     objective = Objective(key=key)
#
#     run: Transaction = Transaction(
#         objective=objective,
#         context=context,
#         emits={},
#         consumes={},
#         state={},
#         daemons={
#             "daemon1": MockDaemon1(),
#             "daemon2": MockDaemon2()
#         }
#     )
#
#     json_str = run.model_dump_json()
#     deserialized_run = Transaction.model_validate_json(json_str)
#
#     assert isinstance(deserialized_run.daemons["daemon1"], MockDaemon1)
#     assert isinstance(deserialized_run.daemons["daemon2"], MockDaemon2)


# def test_run_serialization_with_multiple_signal_groups(context: RunContext) -> None:
#     emits = {
#         "group1": BaseSignals(name="BaseSignals"),
#         "group2": BaseSignals(name="BaseSignals")
#     }
#     consumes = {
#         "group1": BaseSignals(name="BaseSignals"),
#         "group2": BaseSignals(name="BaseSignals")
#     }
#
#     emits["group1"].namespace.signal("signal1")
#     emits["group1"].namespace.signal("signal2")
#     emits["group2"].namespace.signal("signal3")
#
#     consumes["group1"].namespace.signal("signal1")
#     consumes["group1"].namespace.signal("signal2")
#     consumes["group2"].namespace.signal("signal3")
#
#     key = ObjectiveKey(outcome="multi_signal_test")
#     objective = Objective(key=key)
#
#     run: Transaction = Transaction(
#         objective=objective,
#         context=context,
#         emits=emits,
#         consumes=consumes,
#         state={},
#         daemons={}
#     )
#
#     json_str = run.model_dump_json()
#     deserialized_run = Transaction.model_validate_json(json_str)
#
#     assert "signal1" in deserialized_run.execution_context.emits["group1"].namespace
#     assert "signal2" in deserialized_run.execution_context.emits["group1"].namespace
#     assert "signal3" in deserialized_run.execution_context.emits["group2"].namespace
#     assert "signal1" in deserialized_run.execution_context.consumes["group1"].namespace
#     assert "signal2" in deserialized_run.execution_context.consumes["group1"].namespace
#     assert "signal3" in deserialized_run.execution_context.consumes["group2"].namespace


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


# async def test_run_future_results(test_context):
#     # Test that Run's set_result and get_result properly use Objective's future system
#     key = ObjectiveKey(outcome="test")
#     run = Transaction(
#         objective=Objective(key=key),
#         context=test_context,
#         emits={},
#         consumes={},
#         state={},
#         daemons={}
#     )
#
#     # Test setting and getting a result
#     run.objective.set_future_result("test_outcome", None, "test_result")
#     result = run.objective.get_future_result("test_outcome", None)
#     assert result == "test_result"
#
#     # Test setting and getting a result with args_key
#     args_key = {"args": (1, 2), "kwargs": {}}
#     run.objective.set_future_result("test_outcome", args_key, "test_result_with_args")
#     result = run.objective.get_future_result("test_outcome", args_key)
#     assert result == "test_result_with_args"
#
#     # Test getting non-existent result
#     result = run.objective.get_future_result("non_existent", None)
#     assert result is None
#
#     # Test getting result with non-existent args_key
#     key = {"args": (3, 4), "kwargs": {}}
#     result = run.objective.get_future_result("test_outcome", key)
#     assert result is None


# async def test_objective_future_fallback():
#     # Test that when a result is set without args_key, it's used as a fallback
#     obj = Objective(key=ObjectiveKey(outcome="test"))
#
#     # Set a result without args_key
#     obj.set_future_result("test_outcome", None, "fallback_result")
#
#     # Test that any args_key returns the fallback result when use_fallback is True
#     result1 = obj.get_future_result("test_outcome", {"args": (1, 2), "kwargs": {}}, use_fallback=True)
#     assert result1 == "fallback_result"
#
#     result2 = obj.get_future_result("test_outcome", {"args": (3, 4), "kwargs": {}}, use_fallback=True)
#     assert result2 == "fallback_result"
#
#     # Test that setting a specific args_key overrides the fallback
#     args_key = {"args": (1, 2), "kwargs": {}}
#     obj.set_future_result("test_outcome", args_key, "specific_result")
#
#     # The specific args_key should get its result
#     result3 = obj.get_future_result("test_outcome", args_key)
#     assert result3 == "specific_result"
#
#     # Other args_keys should still get the fallback when use_fallback is True
#     result4 = obj.get_future_result("test_outcome", {"args": (3, 4), "kwargs": {}}, use_fallback=True)
#     assert result4 == "fallback_result"


# async def test_run_future_fallback(test_context):
#     # Test that Run's result methods properly handle the fallback behavior
#     run = Transaction(
#         objective=Objective(key=ObjectiveKey(outcome="test")),
#         context=test_context,
#         emits={},
#         consumes={},
#         state={},
#         daemons={}
#     )
#
#     # Set a result without args_key
#     run.objective.set_future_result("test_outcome", None, "fallback_result")
#
#     # Test that any args_key returns the fallback result when use_fallback is True
#     key = {"args": (1, 2), "kwargs": {}}
#     result1 = run.objective.get_future_result("test_outcome", key, True)
#     assert result1 == "fallback_result"
#
#     key1 = {"args": (3, 4), "kwargs": {}}
#     result2 = run.objective.get_future_result("test_outcome", key1, True)
#     assert result2 == "fallback_result"
#
#     # Test that setting a specific args_key overrides the fallback
#     args_key = {"args": (1, 2), "kwargs": {}}
#     run.objective.set_future_result("test_outcome", args_key, "specific_result")
#
#     # The specific args_key should get its result
#     result3 = run.objective.get_future_result("test_outcome", args_key, False)
#     assert result3 == "specific_result"
#
#     # Other args_keys should still get the fallback when use_fallback is True
#     key2 = {"args": (3, 4), "kwargs": {}}
#     result4 = run.objective.get_future_result("test_outcome", key2, True)
#     assert result4 == "fallback_result"


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


def test_create_child_transaction(test_context):
    # Create parent transaction
    parent_objective = Objective(key=ObjectiveKey(outcome="parent", inputs={"parent_input": "value"}))
    parent = Transaction(objective=parent_objective, context=test_context)

    # Create child transaction using helper
    child = parent.create_child_transaction(
        outcome="child",
        inputs={"child_input": "child_value"}
    )

    # Verify child objective is linked to parent
    assert child.objective.of is parent.objective
    assert child.objective.key['outcome'] == "child"
    assert child.objective.key['inputs'] == {"child_input": "child_value"}
    assert child.objective.key['requesting_run'] is parent

    # Verify context was copied
    assert child.context == parent.context
    assert child.context is not parent.context  # Should be a copy

    # Verify bound_contexts was added to async_context_managers
    assert len(child.async_context_managers) > 0


def test_create_child_transaction_with_custom_class(test_context):
    # Create a custom transaction class
    class CustomTransaction(Transaction):
        custom_param: str = Field(default="default_value")

    # Create parent transaction
    parent = Transaction(
        objective=Objective(key=ObjectiveKey(outcome="parent")),
        context=test_context
    )

    # Create child with custom class
    child = parent.create_child_transaction(
        outcome="custom_child",
        transaction_class=CustomTransaction
    )

    # Verify it's the correct class
    assert isinstance(child, CustomTransaction)
    assert child.custom_param == "default_value"
    assert child.objective.of is parent.objective


async def test_child_transaction_context_binding():
    """Test that child transactions properly bind contexts when used"""
    from taskmates.core.workflow_engine.run_context import RunContext

    test_context = RunContext(
        runner_environment={"markdown_path": "test.md", "cwd": "/tmp"},
        run_opts={"model": "test", "max_steps": 10}
    )

    # Track signal connections
    parent_signals_sent = []
    child_signals_sent = []

    # Create parent transaction
    parent = Transaction(
        objective=Objective(key=ObjectiveKey(outcome="parent")),
        context=test_context
    )

    # Connect handlers to track signals
    async def parent_handler(sender, **kwargs):
        parent_signals_sent.append(("parent", sender))

    async def child_handler(sender, **kwargs):
        child_signals_sent.append(("child", sender))

    parent.emits["control"].interrupt.connect(parent_handler)

    # Create child transaction
    child = parent.create_child_transaction(outcome="child")
    child.emits["control"].interrupt.connect(child_handler)

    # Use the transactions
    async with parent.async_transaction_context():
        async with child.async_transaction_context():
            # Send signal from parent - should propagate to child
            await parent.emits["control"].interrupt.send_async({})

    # Verify signal propagation
    assert len(parent_signals_sent) == 1
    assert len(child_signals_sent) == 1  # Child should receive parent's signal


def test_transaction_unified_state_management():
    """Test the unified state management in Transaction"""
    # Create a transaction
    test_context = RunContext(
        runner_environment={"taskmates_dirs": [], "markdown_path": "test.md", "cwd": "/tmp"},
        run_opts={"model": "test", "max_steps": 10}
    )

    transaction = Transaction(
        objective=Objective(key=ObjectiveKey(outcome="test")),
        context=test_context
    )

    # Initial state - future not done, no interrupt
    assert not transaction.result_future.done()
    assert transaction.interrupt_state.value is None
    assert not transaction.should_terminate()

    # Test interrupt states
    transaction.interrupt_state.value = "interrupting"
    assert not transaction.should_terminate()  # Still running, just interrupting

    transaction.interrupt_state.value = "interrupted"
    assert transaction.should_terminate()

    transaction.interrupt_state.value = "killed"
    assert transaction.should_terminate()

    # Reset and test future completion
    transaction.interrupt_state.value = None
    transaction.result_future.set_result("test_result")
    assert transaction.result_future.done()
    assert transaction.should_terminate()
    assert transaction.result_future.result() == "test_result"

    # Test future with exception
    transaction = Transaction(
        objective=Objective(key=ObjectiveKey(outcome="test2")),
        context=test_context
    )
    test_error = ValueError("test error")
    transaction.result_future.set_exception(test_error)
    assert transaction.result_future.done()
    assert transaction.should_terminate()
    with pytest.raises(ValueError, match="test error"):
        transaction.result_future.result()
