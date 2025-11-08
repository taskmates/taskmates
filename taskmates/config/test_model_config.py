import pytest

from taskmates import root_path
from taskmates.config.load_model_config import load_model_config
from taskmates.core.markdown_chat.metadata.config_model_conf import config_model_conf
from taskmates.core.markdown_chat.metadata.calculate_input_tokens import calculate_input_tokens


@pytest.fixture
def taskmates_dirs():
    return [str(root_path() / "taskmates/defaults")]


def test_all_models_can_be_loaded(taskmates_dirs):
    """Test that all models in models.yaml can be loaded."""
    from taskmates.config.load_yaml_config import load_yaml_config
    from taskmates.config.find_config_file import find_config_file

    config_path = find_config_file("models.yaml", taskmates_dirs)
    all_models = load_yaml_config(config_path)

    for model_name in all_models.keys():
        config = load_model_config(model_name, taskmates_dirs)

        assert "metadata" in config, f"Model {model_name} missing metadata section"
        assert "client" in config, f"Model {model_name} missing client section"
        assert "max_context_window" in config["metadata"], f"Model {model_name} missing max_context_window"
        assert "type" in config["client"], f"Model {model_name} missing client type"
        assert "kwargs" in config["client"], f"Model {model_name} missing client kwargs"


def test_all_models_have_valid_structure(taskmates_dirs):
    """Test that all models follow the expected structure."""
    from taskmates.config.load_yaml_config import load_yaml_config
    from taskmates.config.find_config_file import find_config_file

    config_path = find_config_file("models.yaml", taskmates_dirs)
    all_models = load_yaml_config(config_path)

    for model_name, model_config in all_models.items():
        assert isinstance(model_config["metadata"]["max_context_window"], int), \
            f"Model {model_name} has non-integer max_context_window"
        assert model_config["metadata"]["max_context_window"] > 0, \
            f"Model {model_name} has non-positive max_context_window"

        assert isinstance(model_config["client"]["type"], str), \
            f"Model {model_name} has non-string client type"
        assert "." in model_config["client"]["type"], \
            f"Model {model_name} client type is not a valid import path"

        assert isinstance(model_config["client"]["kwargs"], dict), \
            f"Model {model_name} client kwargs is not a dict"
        assert "model" in model_config["client"]["kwargs"], \
            f"Model {model_name} missing model in client kwargs"


def test_openai_models_have_correct_structure(taskmates_dirs):
    """Test OpenAI models have the expected configuration."""
    gpt4o_config = load_model_config("gpt-4o", taskmates_dirs)

    assert gpt4o_config["metadata"]["max_context_window"] == 128000
    assert gpt4o_config["client"]["type"] == "langchain_openai.ChatOpenAI"
    assert gpt4o_config["client"]["kwargs"]["model"] == "gpt-4o"
    assert gpt4o_config["client"]["kwargs"]["openai_api_base"] == "https://api.openai.com/v1"


def test_anthropic_models_have_correct_structure(taskmates_dirs):
    """Test Anthropic models have the expected configuration."""
    claude_config = load_model_config("claude-sonnet-4-5", taskmates_dirs)

    assert claude_config["metadata"]["max_context_window"] == 200000
    assert claude_config["client"]["type"] == "langchain_anthropic.ChatAnthropic"
    assert claude_config["client"]["kwargs"]["model"] == "claude-sonnet-4-5"


def test_ollama_models_have_correct_structure(taskmates_dirs):
    """Test Ollama models have the expected configuration."""
    llama_config = load_model_config("llama4", taskmates_dirs)

    assert llama_config["metadata"]["max_context_window"] == 10485760
    assert llama_config["client"]["type"] == "langchain_ollama.ChatOllama"
    assert llama_config["client"]["kwargs"]["model"] == "llama4:latest"
    assert llama_config["client"]["kwargs"]["base_url"] == "http://localhost:11434"


def test_xai_models_have_api_key_env_reference(taskmates_dirs):
    """Test X.AI models reference API key from environment."""
    grok_config = load_model_config("grok-4", taskmates_dirs)

    assert grok_config["client"]["kwargs"]["api_key"] == "env:XAI_API_KEY"


def test_groq_models_have_correct_structure(taskmates_dirs):
    """Test Groq models have the expected configuration."""
    mixtral_config = load_model_config("mixtral-8x7b-32768", taskmates_dirs)

    assert mixtral_config["metadata"]["max_context_window"] == 32768
    assert mixtral_config["client"]["type"] == "langchain_openai.ChatOpenAI"
    assert mixtral_config["client"]["kwargs"]["openai_api_base"] == "https://api.groq.com/openai/v1"
    assert mixtral_config["client"]["kwargs"]["api_key"] == "env:GROQ_API_KEY"


def test_gemini_models_have_correct_structure(taskmates_dirs):
    """Test Gemini models have the expected configuration."""
    gemini_config = load_model_config("gemini-2.5-pro", taskmates_dirs)

    assert gemini_config["metadata"]["max_context_window"] == 2000000
    assert gemini_config["client"]["type"] == "langchain_google_genai.ChatGoogleGenerativeAI"
    assert gemini_config["client"]["kwargs"]["model"] == "gemini-2.5-pro"


def test_test_models_have_correct_structure(taskmates_dirs):
    """Test fixture/testing models have the expected configuration."""
    echo_config = load_model_config("echo", taskmates_dirs)

    assert echo_config["metadata"]["max_context_window"] == 64000
    assert echo_config["client"][
               "type"] == "taskmates.core.workflows.markdown_completion.completions.llm_completion.testing.echo.Echo"
    assert echo_config["client"]["kwargs"]["model"] == "echo"


def test_calculate_max_tokens_basic():
    """Test basic max_tokens calculation."""
    messages = [
        {"role": "user", "content": "Hello, how are you?"}
    ]

    max_tokens = calculate_input_tokens(messages)

    # Should be less than 4096 (minus input tokens and safety buffer)
    assert max_tokens > 0
    assert max_tokens <= 4096


def test_calculate_max_tokens_with_large_context():
    """Test max_tokens calculation with large context window."""
    messages = [
        {"role": "user", "content": "Short message"}
    ]

    max_tokens = calculate_input_tokens(messages)

    assert max_tokens > 0


def test_calculate_max_tokens_with_images():
    """Test max_tokens calculation with images."""
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What's in this image?"},
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
            ]
        }
    ]

    max_tokens = calculate_input_tokens(messages)

    # Should account for image tokens (100 per image)
    assert max_tokens > 0
    assert max_tokens < 4096  # Less than window due to image tokens


def test_calculate_max_tokens_with_long_conversation():
    """Test max_tokens calculation with long conversation."""
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there! How can I help?"},
        {"role": "user", "content": "I need help with a programming task"},
        {"role": "assistant", "content": "Sure, I'd be happy to help with programming!"},
        {"role": "user", "content": "Can you explain Python decorators?"}
    ]

    max_tokens = calculate_input_tokens(messages)

    # Should leave room for response
    assert max_tokens > 0
    assert max_tokens <= 4096


def test_get_model_conf_includes_all_required_fields(taskmates_dirs):
    """Test that get_model_conf includes all required fields."""
    model_conf = config_model_conf("gpt-4o")

    assert "metadata" in model_conf
    assert "client" in model_conf
    assert "max_tokens" in model_conf["client"]["kwargs"]
    assert "temperature" in model_conf["client"]["kwargs"]
    assert "stop" in model_conf["client"]["kwargs"]


def test_get_model_conf_gpt5_no_temperature(taskmates_dirs):
    """Test that GPT-5 models don't get temperature override."""
    model_conf = config_model_conf("gpt-5")

    # GPT-5 should not have temperature set to 0.2
    assert model_conf["client"]["kwargs"].get("temperature") != 0.2


def test_get_model_conf_non_gpt5_has_temperature(taskmates_dirs):
    """Test that non-GPT-5 models get temperature override."""
    model_conf = config_model_conf("gpt-4o")

    assert model_conf["client"]["kwargs"]["temperature"] == 0.2


def test_get_model_conf_gpt_oss_reasoning_effort(taskmates_dirs):
    """Test that gpt-oss models get reasoning_effort."""
    model_conf = config_model_conf("gpt-oss-20b")

    assert model_conf["client"]["kwargs"]["reasoning_effort"] == "high"


def test_model_alias_with_kwargs_override(taskmates_dirs):
    """Test that model alias with kwargs properly overrides config."""
    model_alias = {
        "name": "gpt-4o",
        "kwargs": {
            "temperature": 0.9,
            "custom_param": "value"
        }
    }

    config = load_model_config(model_alias, taskmates_dirs)

    assert config["client"]["kwargs"]["temperature"] == 0.9
    assert config["client"]["kwargs"]["custom_param"] == "value"
    assert config["client"]["kwargs"]["model"] == "gpt-4o"  # Original should still be there


def test_all_claude_models_have_200k_context(taskmates_dirs):
    """Test that all Claude models have been updated to 200K context."""
    from taskmates.config.load_yaml_config import load_yaml_config
    from taskmates.config.find_config_file import find_config_file

    config_path = find_config_file("models.yaml", taskmates_dirs)
    all_models = load_yaml_config(config_path)

    claude_models = [name for name in all_models.keys() if "claude" in name]

    for model_name in claude_models:
        config = load_model_config(model_name, taskmates_dirs)
        assert config["metadata"]["max_context_window"] == 200000, \
            f"Claude model {model_name} should have 200K context window"


def test_default_model_is_claude(taskmates_dirs):
    """Test that the default model is Claude Sonnet."""
    default_config = load_model_config("default", taskmates_dirs)

    assert default_config["client"]["type"] == "langchain_anthropic.ChatAnthropic"
    assert default_config["client"]["kwargs"]["model"] == "claude-sonnet-4-5"
    assert default_config["metadata"]["max_context_window"] == 200000
