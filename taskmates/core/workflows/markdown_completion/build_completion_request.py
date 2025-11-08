from taskmates.core.markdown_chat.metadata.get_available_tools import get_available_tools
from taskmates.core.markdown_chat.parse_front_matter_and_messages import parse_front_matter_and_messages
from taskmates.core.markdown_chat.participants.compute_participants import compute_participants
from taskmates.defaults.settings import Settings
from taskmates.types import CompletionRequest, RunOpts


def build_completion_request(markdown_chat: str,
                             inputs: dict | None = None,
                             markdown_path: str | None = None,
                             run_opts: RunOpts | None = None) -> CompletionRequest:
    inputs = inputs or {}

    # Parse structure
    front_matter, messages = parse_front_matter_and_messages(
        markdown_chat,
        markdown_path
    )

    # Compute configuration
    recipient_config, participants_configs = compute_participants(front_matter,
                                                                  messages)
    # Get available tools
    available_tools = get_available_tools(front_matter, recipient_config)

    # Process inputs
    front_matter_inputs = front_matter.get("inputs", {})
    combined_inputs = {**front_matter_inputs, **inputs}

    # Build run_opts
    recipient_config_copy = recipient_config.copy()
    recipient_config_copy.pop("name", None)
    recipient_config_copy.pop("description", None)
    recipient_config_copy.pop("system", None)
    recipient_config_copy.pop("role", None)

    # Use provided run_opts or get defaults from Settings
    if run_opts is None:
        settings = Settings.get()
        base_run_opts = settings.get("run_opts", {})
    else:
        base_run_opts = run_opts

    run_opts = {**base_run_opts, **recipient_config_copy, **front_matter, "inputs": combined_inputs}

    chat: CompletionRequest = {
        'run_opts': run_opts,
        'messages': messages,
        'participants': participants_configs,
        'available_tools': list(available_tools.keys())
    }

    return chat


