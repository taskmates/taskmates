# Generated with datamodel-code-generator:
#
# poetry run datamodel-codegen --input github-workflow.json --input-file-type jsonschema --output github_workflow.py --output-model-type typing.TypedDict
#
# Manually adjusted to fix forward references and rename classes with a numeric suffix

from typing import Any, Dict, List, Literal, Optional, TypedDict, Union

from typing_extensions import NotRequired


class WorkflowCallInputs(TypedDict):
    description: NotRequired[str]
    deprecationMessage: NotRequired[str]
    required: NotRequired[bool]
    type: Literal['boolean', 'number', 'string']
    default: NotRequired[Union[bool, float, str]]


class Secrets(TypedDict):
    description: NotRequired[str]
    required: bool


class WorkflowCall(TypedDict):
    inputs: NotRequired[Dict[str, WorkflowCallInputs]]
    secrets: NotRequired[Dict[str, Secrets]]


class WorkflowDispatchInputs(TypedDict):
    description: str
    deprecationMessage: NotRequired[str]
    required: NotRequired[bool]
    default: NotRequired[Any]
    type: NotRequired[Literal['string', 'choice', 'boolean', 'number', 'environment']]
    options: NotRequired[List[str]]


class WorkflowDispatch(TypedDict):
    inputs: NotRequired[Dict[str, WorkflowDispatchInputs]]


class ScheduleItem(TypedDict):
    cron: NotRequired[str]


Architecture = Literal['ARM32', 'x64', 'x86']

Configuration = Union[str, float, bool, Dict[str, 'Configuration'], List['Configuration']]


class Credentials(TypedDict):
    username: NotRequired[str]
    password: NotRequired[str]


Volume = str

PermissionsLevel = Literal['read', 'write', 'none']


class Environment(TypedDict):
    name: str
    url: NotRequired[str]


Event = Literal[
    'branch_protection_rule',
    'check_run',
    'check_suite',
    'create',
    'delete',
    'deployment',
    'deployment_status',
    'discussion',
    'discussion_comment',
    'fork',
    'gollum',
    'issue_comment',
    'issues',
    'label',
    'merge_group',
    'milestone',
    'page_build',
    'project',
    'project_card',
    'project_column',
    'public',
    'pull_request',
    'pull_request_review',
    'pull_request_review_comment',
    'pull_request_target',
    'push',
    'registry_package',
    'release',
    'status',
    'watch',
    'workflow_call',
    'workflow_dispatch',
    'workflow_run',
    'repository_dispatch',
]

EventObject = Optional[Dict[str, Any]]

ExpressionSyntax = str

StringContainingExpressionSyntax = str

Glob = str

Globs = List[Glob]

Machine = Literal['linux', 'macos', 'windows']

Name = str

Path = Globs

Shell = Union[str, Literal['bash', 'pwsh', 'python', 'sh', 'cmd', 'powershell']]

Types = List

WorkingDirectory = str

JobNeeds = Union[List[Name], Name]

Matrix = Union[
    Dict[str, Union[ExpressionSyntax, List[Dict[str, Configuration]]]], ExpressionSyntax
]

Strategy = TypedDict(
    'Strategy',
    {
        'matrix': Matrix,
        'fail-fast': NotRequired[Union[bool, str]],
        'max-parallel': NotRequired[Union[float, str]],
    },
)


class RunsOn(TypedDict):
    group: NotRequired[str]
    labels: NotRequired[Union[str, List[str]]]


class StepUsesMixin(TypedDict):
    uses: str


class StepRunMixin(TypedDict):
    run: str


Branch = Globs

Concurrency = TypedDict(
    'Concurrency',
    {
        'group': str,
        'cancel-in-progress': NotRequired[Union[bool, ExpressionSyntax]],
    },
)

Run = TypedDict(
    'Run',
    {
        'shell': NotRequired[Shell],
        'working-directory': NotRequired[WorkingDirectory],
    },
)


class Defaults(TypedDict):
    run: NotRequired[Run]


PermissionsEvent = TypedDict(
    'PermissionsEvent',
    {
        'actions': NotRequired[PermissionsLevel],
        'attestations': NotRequired[PermissionsLevel],
        'checks': NotRequired[PermissionsLevel],
        'contents': NotRequired[PermissionsLevel],
        'deployments': NotRequired[PermissionsLevel],
        'discussions': NotRequired[PermissionsLevel],
        'id-token': NotRequired[PermissionsLevel],
        'issues': NotRequired[PermissionsLevel],
        'packages': NotRequired[PermissionsLevel],
        'pages': NotRequired[PermissionsLevel],
        'pull-requests': NotRequired[PermissionsLevel],
        'repository-projects': NotRequired[PermissionsLevel],
        'security-events': NotRequired[PermissionsLevel],
        'statuses': NotRequired[PermissionsLevel],
    },
)

Env = Union[Dict[str, Union[str, float, bool]], StringContainingExpressionSyntax]

Ref = TypedDict(
    'Ref',
    {
        'branches': NotRequired[Branch],
        'branches-ignore': NotRequired[Branch],
        'tags': NotRequired[Branch],
        'tags-ignore': NotRequired[Branch],
        'paths': NotRequired[Path],
        'paths-ignore': NotRequired[Path],
    },
)

StepMixin = TypedDict(
    'StepMixin',
    {
        'id': NotRequired[str],
        'if': NotRequired[Union[bool, float, str]],
        'name': NotRequired[str],
        'working-directory': NotRequired[WorkingDirectory],
        'shell': NotRequired[Shell],
        'with': NotRequired[Env],
        'env': NotRequired[Env],
        'continue-on-error': NotRequired[Union[bool, ExpressionSyntax]],
        'timeout-minutes': NotRequired[Union[float, ExpressionSyntax]],
    },
)


class StepWithUses(StepUsesMixin, StepMixin):
    pass


class StepWithRun(StepRunMixin, StepMixin):
    pass


Step = Union[StepWithUses, StepWithRun]


class On(TypedDict):
    branch_protection_rule: NotRequired[EventObject]
    check_run: NotRequired[EventObject]
    check_suite: NotRequired[EventObject]
    create: NotRequired[EventObject]
    delete: NotRequired[EventObject]
    deployment: NotRequired[EventObject]
    deployment_status: NotRequired[EventObject]
    discussion: NotRequired[EventObject]
    discussion_comment: NotRequired[EventObject]
    fork: NotRequired[EventObject]
    gollum: NotRequired[EventObject]
    issue_comment: NotRequired[EventObject]
    issues: NotRequired[EventObject]
    label: NotRequired[EventObject]
    merge_group: NotRequired[EventObject]
    milestone: NotRequired[EventObject]
    page_build: NotRequired[EventObject]
    project: NotRequired[EventObject]
    project_card: NotRequired[EventObject]
    project_column: NotRequired[EventObject]
    public: NotRequired[EventObject]
    pull_request: NotRequired[Ref]
    pull_request_review: NotRequired[EventObject]
    pull_request_review_comment: NotRequired[EventObject]
    pull_request_target: NotRequired[Ref]
    push: NotRequired[Ref]
    registry_package: NotRequired[EventObject]
    release: NotRequired[EventObject]
    status: NotRequired[EventObject]
    watch: NotRequired[EventObject]
    workflow_call: NotRequired[WorkflowCall]
    workflow_dispatch: NotRequired[WorkflowDispatch]
    workflow_run: NotRequired[EventObject]
    repository_dispatch: NotRequired[EventObject]
    schedule: NotRequired[List[ScheduleItem]]


class Container(TypedDict):
    image: str
    credentials: NotRequired[Credentials]
    env: NotRequired[Env]
    ports: NotRequired[List[Union[float, str]]]
    volumes: NotRequired[List[Volume]]
    options: NotRequired[str]


Permissions = Union[Literal['read-all', 'write-all'], PermissionsEvent]

ReusableWorkflowCallJob = TypedDict(
    'ReusableWorkflowCallJob',
    {
        'name': NotRequired[str],
        'signals': NotRequired[JobNeeds],
        'permissions': NotRequired[Permissions],
        'if': NotRequired[Union[bool, float, str]],
        'uses': str,
        'with': NotRequired[Env],
        'secrets': NotRequired[Union[Env, Literal['inherit']]],
        'strategy': NotRequired[Strategy],
        'concurrency': NotRequired[Union[str, Concurrency]],
    },
)

NormalJob = TypedDict(
    'NormalJob',
    {
        'name': NotRequired[str],
        'signals': NotRequired[JobNeeds],
        'permissions': NotRequired[Permissions],
        'runs-on': Union[
            str, List, RunsOn, StringContainingExpressionSyntax, ExpressionSyntax
        ],
        'environment': NotRequired[Union[str, Environment]],
        'outputs': NotRequired[Dict[str, str]],
        'env': NotRequired[Env],
        'defaults': NotRequired[Defaults],
        'if': NotRequired[Union[bool, float, str]],
        'steps': NotRequired[List[Step]],
        'timeout-minutes': NotRequired[Union[float, ExpressionSyntax]],
        'strategy': NotRequired[Strategy],
        'continue-on-error': NotRequired[Union[bool, ExpressionSyntax]],
        'container': NotRequired[Union[str, Container]],
        'services': NotRequired[Dict[str, Container]],
        'concurrency': NotRequired[Union[str, Concurrency]],
    },
)

Model = TypedDict(
    'Model',
    {
        'name': NotRequired[str],
        'on': Union[Event, List[Event], On],
        'env': NotRequired[Env],
        'defaults': NotRequired[Defaults],
        'concurrency': NotRequired[Union[str, Concurrency]],
        'daemons': Dict[str, Union[NormalJob, ReusableWorkflowCallJob]],
        'run-name': NotRequired[str],
        'permissions': NotRequired[Permissions],
    },
)
