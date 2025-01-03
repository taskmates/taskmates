from typing import Any, Optional, Dict, List, Union

from pydantic import BaseModel, Field, ConfigDict, model_validator
from typeguard import typechecked

from taskmates.workflow_engine.daemon import Daemon
from taskmates.workflow_engine.default_environment_signals import default_environment_signals
from taskmates.workflows.contexts.context import Context


@typechecked
class Objective(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra='allow'  # Allow extra fields that aren't serialized
    )

    outcome: Optional[str] = None
    inputs: Optional[Dict[str, Any]] = Field(default_factory=dict)
    requester: Optional[Any] = Field(default=None, exclude=True)  # exclude from serialization
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
        from taskmates.workflow_engine.run import Run

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
        from taskmates.workflow_engine.run import Run

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
