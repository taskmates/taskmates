import asyncio
import contextvars
from contextlib import AbstractAsyncContextManager, ExitStack, AsyncExitStack, contextmanager, asynccontextmanager
from typing import TypedDict, Dict, Any, Sequence, Optional

from pydantic import BaseModel, ConfigDict, Field
from typeguard import typechecked

from taskmates.core.workflow_engine.base_signals import BaseSignals
from taskmates.core.workflow_engine.objective import Objective, ObjectiveKey
from taskmates.core.workflow_engine.run_context import RunContext
from taskmates.core.workflows.signals.control_signals import ControlSignals
from taskmates.core.workflows.signals.execution_environment_signals import ExecutionEnvironmentSignals
from taskmates.core.workflows.signals.input_streams_signals import InputStreamsSignals
from taskmates.core.workflows.signals.status_signals import StatusSignals
from taskmates.core.workflows.states.interrupt_state import InterruptState
from taskmates.lib.context_.temp_context import temp_context
from taskmates.lib.contextlib_.ensure_async_context_manager import ensure_async_context_manager
from taskmates.taskmates_runtime import TASKMATES_RUNTIME


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

    of: Any = Field(default=None, exclude=True)

    objective: Objective

    context: RunContext = Field(default_factory=dict)

    emits: Dict[str, BaseSignals] = Field(default_factory=dict)
    consumes: Dict[str, BaseSignals] = Field(default_factory=dict)
    state: Dict[str, Any] = Field(default_factory=dict)
    resources: Dict[str, Any] = Field(default_factory=dict)

    # Unified state management
    result_future: asyncio.Future = Field(default_factory=asyncio.Future, exclude=True)
    interrupt_state: 'InterruptState' = Field(default_factory=lambda: InterruptState(), exclude=True)
    completed: bool = Field(default=False, exclude=True)

    # Logger for transaction-scoped logging
    logger: Any = Field(default=None, exclude=True)

    # Runtime-only fields, excluded from serialization

    # namespace: Namespace = Field(default_factory=Namespace, exclude=True)

    # daemons: Dict[str, AbstractContextManager] = Field(default_factory=dict)
    async_context_managers: Sequence[AbstractAsyncContextManager] = Field(default_factory=list)
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

    # async def run_steps(self, steps: Any) -> Any:
    #     self.objective.runs.append(self)
    #
    #     runner = Runner(func=steps, inputs=self.objective.key['inputs'])
    #
    #     with tracer.start_as_current_span(
    #             format_span_name(steps, self.objective),
    #             kind=trace.SpanKind.INTERNAL
    #     ):
    #         async with self.async_transaction_context():
    #             runner.start()
    #             return await runner.get_result()

    def bind_to_parent(self, parent_transaction: 'Transaction'):
        # Bind parent and child transactions
        from taskmates.core.workflows.markdown_completion.bound_contexts import bound_contexts
        bound_context_manager = ensure_async_context_manager(
            bound_contexts(parent_transaction, self))
        self.async_context_managers = list(self.async_context_managers) + [
            bound_context_manager]

    def create_child_transaction(self,
                                 outcome: str,
                                 inputs: Optional[Dict[str, Any]] = None,
                                 result_format=None):

        # Create the child objective linked to the parent
        child_objective = Objective(
            of=self.objective,
            key=ObjectiveKey(
                outcome=outcome,
                inputs=inputs or {},
            ),
            **({"result_format": result_format} if result_format else {})
        )

        child_transaction = Transaction(of=self, objective=child_objective, context=self.context.copy())
        child_transaction.bind_to_parent(self)

        return child_transaction

    def create_bound_transaction(self,
                                 operation,
                                 inputs: Optional[Dict[str, Any]] = None,
                                 result_format=None):

        from taskmates.core.workflow_engine.transaction_manager import runtime
        manager = runtime.transaction_manager()
        child_transaction = manager.build_executable_transaction(
            of=self,
            operation=operation.operation,
            outcome=operation.outcome,
            inputs=inputs,
            result_format=result_format,
            context=self.context.copy(),
            workflow_instance=operation._instance,
            max_retries=operation.max_retries,
            initial_delay=operation.initial_delay
        )
        child_transaction.bind_to_parent(self)

        return child_transaction

    def done(self) -> bool:
        return self.completed

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


TRANSACTION: contextvars.ContextVar[Transaction] = contextvars.ContextVar('Transaction', default=None)
