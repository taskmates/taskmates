import re
from typing import AsyncIterable, List

import pytest

from taskmates.lib.openai_.model.chat_completion_chunk_model import ChatCompletionChunkModel
from taskmates.lib.openai_.model.choice_model import ChoiceModel
from taskmates.lib.openai_.model.delta_model import DeltaModel


class ChatCompletionPreProcessor:
    def __init__(self, chat_completion: AsyncIterable[ChatCompletionChunkModel]):
        self.chat_completion = chat_completion
        self.name = None

    async def __aiter__(self):
        async for chunk in self.chat_completion:
            if chunk.choices[0].delta.content is None:
                yield chunk
                continue

            content = chunk.choices[0].delta.content
            content = content.lstrip()  # Remove leading spaces from all chunks

            if content and re.match(r'^[#*\->`\[\]{}]', content):
                content = "\n" + content

            if content:  # Skip empty content chunks
                chunk.choices[0].delta.content = content
                yield chunk


async def mock_chat_completion_generator(content_list: List[str], model: str = 'mock_model'):
    yield ChatCompletionChunkModel(
        choices=[ChoiceModel(delta=DeltaModel(role='assistant', content=''))],
        model=model
    )
    for content in content_list:
        yield ChatCompletionChunkModel(
            choices=[ChoiceModel(delta=DeltaModel(content=content))],
            model=model
        )
    yield ChatCompletionChunkModel(
        choices=[ChoiceModel(delta=DeltaModel(content=None), finish_reason='stop')],
        model=model
    )


@pytest.mark.asyncio
async def test_chat_completion_pre_processor_no_changes():
    content_list = ['Hello', ' World']
    pre_processor = ChatCompletionPreProcessor(mock_chat_completion_generator(content_list))

    chunks = [chunk async for chunk in pre_processor]
    texts = [chunk.choices[0].delta.content for chunk in chunks if chunk.choices[0].delta.content is not None]

    assert texts == ['Hello', 'World']


@pytest.mark.asyncio
async def test_chat_completion_pre_processor_strip_leading_space():
    content_list = [' Hello', ' World']
    pre_processor = ChatCompletionPreProcessor(mock_chat_completion_generator(content_list))

    chunks = [chunk async for chunk in pre_processor]
    texts = [chunk.choices[0].delta.content for chunk in chunks if chunk.choices[0].delta.content is not None]

    assert texts == ['Hello', 'World']


@pytest.mark.asyncio
async def test_chat_completion_pre_processor_add_newline_list():
    content_list = ['* Hello', ' World']
    pre_processor = ChatCompletionPreProcessor(mock_chat_completion_generator(content_list))

    chunks = [chunk async for chunk in pre_processor]
    texts = [chunk.choices[0].delta.content for chunk in chunks if chunk.choices[0].delta.content is not None]

    assert texts == ['\n* Hello', 'World']


@pytest.mark.asyncio
async def test_chat_completion_pre_processor_add_newline_heading():
    content_list = ['# Hello', ' World']
    pre_processor = ChatCompletionPreProcessor(mock_chat_completion_generator(content_list))

    chunks = [chunk async for chunk in pre_processor]
    texts = [chunk.choices[0].delta.content for chunk in chunks if chunk.choices[0].delta.content is not None]

    assert texts == ['\n# Hello', 'World']


@pytest.mark.asyncio
async def test_chat_completion_pre_processor_add_newline_code_block():
    content_list = ['```python', 'print("Hello")']
    pre_processor = ChatCompletionPreProcessor(mock_chat_completion_generator(content_list))

    chunks = [chunk async for chunk in pre_processor]
    texts = [chunk.choices[0].delta.content for chunk in chunks if chunk.choices[0].delta.content is not None]

    assert texts == ['\n```python', 'print("Hello")']


@pytest.mark.asyncio
async def test_chat_completion_pre_processor_no_newline_regular_text():
    content_list = ['This is regular text', ' without Markdown']
    pre_processor = ChatCompletionPreProcessor(mock_chat_completion_generator(content_list))

    chunks = [chunk async for chunk in pre_processor]
    texts = [chunk.choices[0].delta.content for chunk in chunks if chunk.choices[0].delta.content is not None]

    assert texts == ['This is regular text', 'without Markdown']


@pytest.mark.asyncio
async def test_chat_completion_pre_processor_multiple_chunks():
    content_list = [' # Heading', ' * List item', ' > Blockquote', ' Regular text']
    pre_processor = ChatCompletionPreProcessor(mock_chat_completion_generator(content_list))

    chunks = [chunk async for chunk in pre_processor]
    texts = [chunk.choices[0].delta.content for chunk in chunks if chunk.choices[0].delta.content is not None]

    assert texts == ['\n# Heading', '\n* List item', '\n> Blockquote', 'Regular text']


@pytest.mark.asyncio
async def test_chat_completion_pre_processor_no_content():
    content_list = ['']
    pre_processor = ChatCompletionPreProcessor(mock_chat_completion_generator(content_list))

    chunks = [chunk async for chunk in pre_processor]
    texts = [chunk.choices[0].delta.content for chunk in chunks if chunk.choices[0].delta.content is not None]

    assert texts == []
