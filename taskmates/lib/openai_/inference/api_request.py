import asyncio

import pytest
from httpx import ReadError
from typeguard import typechecked

from taskmates.core.actions.chat_completion.openai_adapters.anthropic_openai_adapter.response.chat_completion_pre_processor import \
    ChatCompletionPreProcessor
from taskmates.core.actions.chat_completion.openai_adapters.anthropic_openai_adapter.response.chat_completion_with_username import \
    ChatCompletionWithUsername
from taskmates.formats.markdown.metadata.get_model_client import get_model_client
from taskmates.lib.openai_.inference.interruptible_request import InterruptibleRequest
from taskmates.lib.opentelemetry_.tracing import tracer
from taskmates.server.streamed_response import StreamedResponse
from taskmates.workflow_engine.run import RUN, Run


@typechecked
async def api_request(client, request_payload: dict, current_run: Run) -> dict:
    streamed_response = StreamedResponse()
    output_streams = current_run.signals["output_streams"]
    control = current_run.signals["control"]
    status = current_run.signals["status"]

    with tracer().start_as_current_span(name="chat-completion"):
        async with InterruptibleRequest(status=status, control=control) as request:
            chat_completion = await client.chat.completions.create(**request_payload)

            if request_payload.get("stream", False):
                output_streams.chat_completion.connect(streamed_response.accept, weak=False)

                try:
                    async for chat_completion_chunk in \
                            ChatCompletionWithUsername(ChatCompletionPreProcessor(chat_completion)):
                        if request.interrupted_or_killed:
                            break
                        await output_streams.chat_completion.send_async(chat_completion_chunk)

                except asyncio.CancelledError:
                    await output_streams.artifact.send_async(
                        {"name": "response_cancelled.json", "content": str(True)})
                    raise
                except ReadError as e:
                    await output_streams.artifact.send_async(
                        {"name": "response_read_error.json", "content": str(e)})

                response = streamed_response.payload
            else:
                response = chat_completion.model_dump()

    await output_streams.artifact.send_async({"name": "response.json", "content": response})

    if not response['choices']:
        # NOTE: this seems to happen when the request is cancelled before any response is received
        raise asyncio.CancelledError

    if response['choices'][0]['finish_reason'] == 'length':
        raise Exception("OpenAI API response was truncated.")

    return response


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_request_happy_path(run):
    # Define the model configuration and parameters as per your actual use case
    model_conf = {
        "model": "echo"
    }
    model_params = {
        # Add any additional parameters required by your model here
    }
    messages = [
        # Add the messages that you want to send to the model here
        {"role": "user", "content": "Answer with a single number. 1 + 1="},
    ]

    # Call the api_request function with the defined parameters
    contexts = RUN.get().context
    client = get_model_client(model_conf["model"], contexts["runner_config"]["taskmates_dirs"])
    response = await api_request(client, messages, model_conf, model_params, run)

    # Assert that the response is as expected
    assert 'choices' in response
    assert isinstance(response['choices'], list)
    assert 'message' in response['choices'][0]
    assert 'content' in response['choices'][0]['message']
    assert response['choices'][0]['message']['content']  # Check if content is not empty


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_request_with_complex_payload(run):
    # Define the complex payload based on the JSON you provided
    messages = [
        {
            "content": "what is on https://asurprisingimage.com?\n",
            "role": "user"
        },
        {
            "content": None,
            "role": "assistant",
            "tool_calls": [
                {
                    "function": {
                        "arguments": "{\"url\":\"https://asurprisingimage.com\"}",
                        "name": "visit_page"
                    },
                    "id": "tool_call_1701668882083",
                    "type": "function"
                }
            ]
        },
        {
            "content": "[cat.jpeg](..%2F..%2F..%2F..%2F..%2FDownloads%2Fcat.jpeg)\n",
            "name": "visit_page",
            "role": "tool",
            "tool_call_id": "tool_call_1701668882083"
        },
        {
            "role": "assistant",
            "content": "![[/Users/ralphus/Downloads/cat.jpeg]]\n\nI can see a cat in the image."
        }
    ]

    model_conf = {
        "model": "gpt-3.5-turbo",
        "stream": True,
        "temperature": 0.2,
        "max_tokens": 4096,
        "tools": [{
            "type": "function",
            "function": {
                "name": "visit_page",
                "description": "Visits a page",
                "parameters": {
                    "properties": {
                        "url": {
                            "description": "the url"
                        }
                    },
                    "required": ["url"],
                    "type": "object"
                }
            }
        }]
    }
    model_params = {}

    # Call the api_request function with the defined parameters
    contexts = RUN.get().context
    client = get_model_client(model_conf["model"], contexts["runner_config"]["taskmates_dirs"])
    response = await api_request(client, messages, model_conf, model_params, run)

    # Assert that the response is as expected
    assert 'choices' in response
    assert isinstance(response['choices'], list)
    assert len(response['choices']) > 0  # There should be at least one choice in the response
    assert 'message' in response['choices'][0]
    assert 'content' in response['choices'][0]['message']
    assert response['choices'][0]['message']['content']  # Content should not be empty
