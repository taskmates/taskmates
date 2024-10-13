import asyncio
from random import random

import pytest
from httpx import ReadError
from typeguard import typechecked

from taskmates.core.actions.chat_completion.openai_adapters.anthropic_openai_adapter.response.chat_completion_pre_processor import \
    ChatCompletionPreProcessor
from taskmates.core.actions.chat_completion.openai_adapters.anthropic_openai_adapter.response.chat_completion_with_username import \
    ChatCompletionWithUsername
from taskmates.core.run import RUN, Run
from taskmates.formats.markdown.metadata.get_model_client import get_model_client
from taskmates.lib.not_set.not_set import NOT_SET
from taskmates.lib.opentelemetry_.tracing import tracer
from taskmates.server.streamed_response import StreamedResponse


@typechecked
async def api_request(client, messages: list, model_conf: dict, model_params: dict,
                      run: Run) -> dict:
    streamed_response = StreamedResponse()
    run.output_streams.chat_completion.connect(streamed_response.accept, weak=False)

    if run.output_streams.chat_completion.receivers:
        model_conf.update({"stream": True})

    llm_client_args = get_llm_client_args(messages, model_conf, model_params)

    with tracer().start_as_current_span(name="chat-completion"):
        await run.output_streams.artifact.send_async(
            {"name": "openai_request_payload.json", "content": llm_client_args})

        interrupted_or_killed = False

        async def interrupt_handler(sender):
            nonlocal interrupted_or_killed
            interrupted_or_killed = True
            await chat_completion.response.aclose()
            await run.status.interrupted.send_async(None)

        async def kill_handler(sender):
            nonlocal interrupted_or_killed
            interrupted_or_killed = True
            await chat_completion.response.aclose()
            await run.status.killed.send_async(None)

        with run.control.interrupt.connected_to(interrupt_handler), \
                run.control.kill.connected_to(kill_handler):
            chat_completion = await client.chat.completions.create(**llm_client_args)

            if model_conf["stream"]:
                try:
                    async for chat_completion_chunk in \
                            ChatCompletionWithUsername(ChatCompletionPreProcessor(chat_completion)):
                        if interrupted_or_killed:
                            break
                        for choice in chat_completion_chunk.choices:
                            if choice.delta.content:
                                content: str = choice.delta.content
                                # TODO move this to ChatCompletionPreProcessor
                                choice.delta.content = content.replace("\r", "")
                        await run.output_streams.chat_completion.send_async(chat_completion_chunk)

                except asyncio.CancelledError:
                    await run.output_streams.artifact.send_async(
                        {"name": "response_cancelled.json", "content": str(True)})
                    await chat_completion.response.aclose()
                    raise
                except ReadError as e:
                    await run.output_streams.artifact.send_async(
                        {"name": "response_read_error.json", "content": str(e)})

                response = streamed_response.payload
            else:
                response = chat_completion.model_dump()

    await run.output_streams.artifact.send_async({"name": "response.json", "content": response})

    if not response['choices']:
        # NOTE: this seems to happen when the request is cancelled before any response is received
        raise asyncio.CancelledError

    if response['choices'][0]['finish_reason'] == 'length':
        raise Exception("OpenAI API response was truncated.")

    return response


def get_llm_client_args(messages, model_conf, model_params):
    if model_params.get("tool_choice", None) is NOT_SET:
        del model_params["tool_choice"]
    if "tools" in model_params and not model_params["tools"]:
        del model_params["tools"]
    seed = int(random() * 1000000)
    llm_client_args = (dict(messages=messages, **model_conf, **model_params, seed=seed))
    return llm_client_args


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
    contexts = RUN.get().contexts
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
            "content": [
                {
                    "text": "![[/Users/ralphus/Downloads/cat.jpeg]]\n\n",
                    "type": "text"
                },
                {
                    "image_url": {
                        "url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYII=",
                    },
                    "type": "image_url"
                }
            ],
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

    # Assuming the SIGNALS and CURRENT_PATH are properly initialized
    # and the OpenAI API key is set in the environment or configuration

    # Call the api_request function with the defined parameters
    contexts = RUN.get().contexts
    client = get_model_client(model_conf["model"], contexts["runner_config"]["taskmates_dirs"])
    response = await api_request(client, messages, model_conf, model_params, run)

    # Assert that the response is as expected
    assert 'choices' in response
    assert isinstance(response['choices'], list)
    assert len(response['choices']) > 0  # There should be at least one choice in the response
    assert 'message' in response['choices'][0]
    assert 'content' in response['choices'][0]['message']
    assert response['choices'][0]['message']['content']  # Content should not be empty
    # Add more specific assertions based on the expected response structure
