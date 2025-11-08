import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, Hashable

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typeguard import typechecked

from taskmates.types import ResultFormat


@typechecked
class ObjectiveKey(Dict[str, Any]):
    def __init__(self,
                 outcome: Optional[str] = None,
                 inputs: Optional[Dict[str, Any]] = None,
                 scope: Optional[Hashable] = None,
                 ) -> None:
        super().__init__()
        self['outcome'] = outcome
        self['inputs'] = inputs or {}  # args
        self['scope'] = scope or datetime.now()  # scope
        # self['requesting_run'] = requesting_run  # context
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
    # sub_objectives: Dict[ObjectiveKey, 'Objective'] = Field(default_factory=dict, exclude=True)

    result_future: asyncio.Future = Field(default_factory=asyncio.Future, exclude=True)
    result_format: ResultFormat = {'format': 'completion', 'interactive': False}

    # runs: List[Any] = Field(default_factory=list, exclude=True)

    @field_validator('key', mode='before')
    @classmethod
    def validate_key(cls, value: Any) -> ObjectiveKey:
        if isinstance(value, dict):
            return ObjectiveKey(
                outcome=value.get('outcome'),
                inputs=value.get('inputs', {}),
                # requesting_run=value.get('requesting_run')
            )
        return value

    @model_validator(mode='before')
    @classmethod
    def convert_inputs(cls, data: Any) -> Any:
        if isinstance(data, dict) and 'inputs' in data and data['inputs'] is None:
            data['inputs'] = {}
        return data

    # def get_or_create_sub_objective(self,
    #                                 outcome: str,
    #                                 inputs: Optional[Dict[str, Any]] = None) -> 'Objective':
    #     key = ObjectiveKey(outcome=outcome, inputs=inputs or {})
    #     if key not in self.sub_objectives:
    #         sub_objective = Objective(of=self, key=ObjectiveKey(outcome=outcome, inputs=inputs or {}))
    #         self.sub_objectives[key] = sub_objective
    #     return self.sub_objectives[key]

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
        root = self._get_root()
        print(root.dump_graph(current_objective=self))


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

# def test_objective_dump_graph_with_current():
#     # Create a root objective
#     root = Objective(key=ObjectiveKey(outcome="root", inputs={"root_input": "value"}))
#
#     # Create some sub-objectives
#     sub1 = root.get_or_create_sub_objective("child1", {"child1_input": "value1"})
#     root.get_or_create_sub_objective("child2", {"child2_input": "value2"})
#
#     # Create a sub-sub-objective
#     sub1.get_or_create_sub_objective("grandchild1", {"grandchild1_input": "value3"})
#
#     # Get the graph representation when called from sub1
#     graph = root.dump_graph(current_objective=sub1)
#
#     # Verify that sub1 shows as CURRENT and others show as PENDING
#     assert "child1" in graph
#     assert "CURRENT..." in graph
#     assert "PENDING..." in graph
#     assert graph.count("CURRENT...") == 1  # Only one objective should be marked as current
#     assert graph.count("PENDING...") >= 1  # At least one objective should be marked as pending
#
#     # Test that the structure is maintained
#     lines = graph.split("\n")
#     assert lines[0].startswith("└──")  # Root level
#     assert all(line.startswith("    ") for line in lines[1:])  # Indented children
