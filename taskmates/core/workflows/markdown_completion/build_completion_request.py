from taskmates.core.markdown_chat.metadata.get_available_tools import get_available_tools
from taskmates.core.markdown_chat.parse_front_matter_and_messages import parse_front_matter_and_messages
from taskmates.core.markdown_chat.participants.compute_participants import compute_participants
from taskmates.defaults.settings import Settings
from taskmates.types import CompletionRequest, RunOpts


def build_completion_request(markdown_chat: str,
                             markdown_path: str | None = None,
                             run_opts: RunOpts | None = None) -> CompletionRequest:

    # Parse structure
    front_matter, messages = parse_front_matter_and_messages(
        markdown_chat,
        markdown_path
    )

    # TODO: split this method

    # Compute configuration
    recipient_config, participants_configs = compute_participants(front_matter,
                                                                  messages)
    # Get available tools
    available_tools = get_available_tools(front_matter, recipient_config)

    # Build run_opts

    # Use provided run_opts or get defaults from Settings
    if run_opts is None:
        settings = Settings.get()
        base_run_opts = settings.get("run_opts", {})
    else:
        base_run_opts = run_opts

    recipient_config_run_opts = recipient_config.get("run_opts", {})

    run_opts = {**base_run_opts, **recipient_config_run_opts, **front_matter}

    chat: CompletionRequest = {
        'run_opts': run_opts,
        'messages': messages,
        'participants': participants_configs,
        'available_tools': list(available_tools.keys())
    }

    return chat
