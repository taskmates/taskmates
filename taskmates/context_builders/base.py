from taskmates.context_builders.api_context_builder import ApiContextBuilder
from taskmates.context_builders.cli_context_builder import CliContextBuilder
from taskmates.context_builders.context_builder import ContextBuilder
from taskmates.context_builders.default_context_builder import DefaultContextBuilder
from taskmates.context_builders.sdk_context_builder import SdkContextBuilder
from taskmates.context_builders.test_context_builder import TestContextBuilder

__all__ = [
    'ContextBuilder',
    'DefaultContextBuilder',
    'CliContextBuilder',
    'ApiContextBuilder',
    'SdkContextBuilder',
    'TestContextBuilder'
]


def test_context_builders():
    import pytest
    from types import SimpleNamespace

    # Test DefaultContextBuilder
    default_contexts = DefaultContextBuilder().build()
    assert isinstance(default_contexts, dict)
    assert "client_config" in default_contexts
    assert "completion_opts" in default_contexts

    # Test CliContextBuilder
    args = SimpleNamespace(model="test-model", template_params=[{"key1": "value1"}], max_steps=5, format="json",
                           endpoint="test-endpoint")
    cli_contexts = CliContextBuilder(args).build()
    assert cli_contexts["completion_opts"]["model"] == "test-model"
    assert cli_contexts["completion_opts"]["max_steps"] == 5
    assert cli_contexts["client_config"]["format"] == "json"
    assert cli_contexts["client_config"]["endpoint"] == "test-endpoint"

    # Test ApiContextBuilder
    payload = {
        "completion_context": {"test_key": "test_value"},
        "completion_opts": {"model": "api-model"}
    }
    api_contexts = ApiContextBuilder(payload).build()
    assert api_contexts["completion_context"]["test_key"] == "test_value"
    assert api_contexts["completion_opts"]["model"] == "api-model"
    assert api_contexts["client_config"]["interactive"] == True

    # Test SdkContextBuilder
    sdk_opts = {"model": "sdk-model", "max_steps": 3}
    sdk_contexts = SdkContextBuilder(sdk_opts).build()
    assert sdk_contexts["completion_opts"]["model"] == "sdk-model"
    assert sdk_contexts["completion_opts"]["max_steps"] == 3
    assert sdk_contexts["client_config"]["interactive"] == True

    # Test TestContextBuilder
    with pytest.raises(TypeError):
        # This should raise an error because we're not passing a tmp_path
        TestContextBuilder().build()

    # We can't easily test TestContextBuilder without a real tmp_path,
    # which is typically provided by pytest. For a real test, you'd use
    # the pytest.fixture for tmp_path.
