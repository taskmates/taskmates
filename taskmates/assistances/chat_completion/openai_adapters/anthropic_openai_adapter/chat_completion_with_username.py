import re
from typing import AsyncIterable, List

import pytest

from taskmates.lib.openai_.model.chat_completion_chunk_model import ChatCompletionChunkModel
from taskmates.lib.openai_.model.choice_model import ChoiceModel
from taskmates.lib.openai_.model.delta_model import DeltaModel


class ChatCompletionWithUsername:
    def __init__(self, chat_completion: AsyncIterable[ChatCompletionChunkModel]):
        self.chat_completion = chat_completion
        self.buffered_tokens: List[str] = []
        self.buffering = True

    async def __aiter__(self):
        async for chunk in self.chat_completion:
            if chunk.choices[0].delta.content is None:
                yield chunk
                continue

            current_token = chunk.choices[0].delta.content

            if not self.buffering:
                yield self._create_chunk(chunk, current_token)
                continue

            self.buffered_tokens.append(current_token)

            full_content = "".join(self.buffered_tokens)

            if self._is_full_match(full_content):
                match = re.match(r'^[ \n]*\*\*([^*]+)>\*\*[ \n]+', "".join(self.buffered_tokens))
                username = match.group(1)
                yield self._flush_username(chunk, username)
                remaining_content = self._extract_remaining_content(full_content)
                if remaining_content:
                    yield self._create_chunk(chunk, remaining_content)
                self.buffering = False
                self.buffered_tokens = []
            elif not self._is_partial_match(full_content):
                yield self._flush_username(chunk, None)
                yield self._create_chunk(chunk, full_content)
                self.buffering = False
                self.buffered_tokens = []

    @staticmethod
    def _is_full_match(content: str) -> bool:
        return bool(re.match(r'^[ \n]*\*\*([^*]+)>\*\*[ \n]+', content))

    @staticmethod
    def _is_partial_match(content: str) -> bool:
        return content == '' or re.match(r'^[ \n]*\*\*[^*]*\*?\*?[ \n]?$', content)

    def _flush_username(self, chunk: ChatCompletionChunkModel, username) -> ChatCompletionChunkModel:
        return self._create_chunk(chunk, '', 'assistant', username)

    @staticmethod
    def _extract_remaining_content(content: str) -> str:
        match = re.match(r'^[ \n]*\*\*([^*]+)>\*\*[ \n]+(.*)', content, re.DOTALL)
        return match.group(2) if match else ''

    @staticmethod
    def _create_chunk(original_chunk: ChatCompletionChunkModel, content: str,
                      role: str = None,
                      name: str = None) -> ChatCompletionChunkModel:
        choice = ChoiceModel(
            delta=DeltaModel(content=content, name=name, role=role),
            finish_reason=original_chunk.choices[0].finish_reason,
            index=original_chunk.choices[0].index,
            logprobs=original_chunk.choices[0].logprobs,
        )
        return ChatCompletionChunkModel(
            id=original_chunk.id,
            choices=[choice],
            created=original_chunk.created,
            model=original_chunk.model,
            object=original_chunk.object,
            system_fingerprint=original_chunk.system_fingerprint,
        )


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
async def test_buffered_chat_completion_wrapper_without_username(tmp_path):
    content_list = ['He', 'llo']
    wrapper = ChatCompletionWithUsername(mock_chat_completion_generator(content_list))

    chunks = [chunk async for chunk in wrapper]
    texts = [chunk.choices[0].delta.content for chunk in chunks if chunk.choices[0].delta.content]
    assert "".join(texts) == "Hello"


@pytest.mark.asyncio
@pytest.mark.parametrize("content_list", [
    ['**', 'jo', 'hn', '>', '**', ' ', 'He', 'llo'],
    ['**', 'jo', 'hn', '>', '**', '\n', 'He', 'llo'],
    ['**', 'jo', 'hn>', '**', ' ', 'He', 'llo'],
    ['**', 'jo', 'hn', '>**', ' ', 'He', 'llo'],
    ['**', 'jo', 'hn>', '**', ' He', 'llo'],
    ['**john>**', ' Hello'],
    ['**john>** ', 'Hello'],
    ['**john>** Hello'],
    ['**john>**\nHello'],
    ['  **john>** Hello'],
    ['\n\n**john>**\nHello'],
])
async def test_buffered_chat_completion_wrapper_with_username(tmp_path, content_list):
    wrapper = ChatCompletionWithUsername(mock_chat_completion_generator(content_list))

    chunks = [chunk async for chunk in wrapper]

    texts = [chunk.choices[0].delta.content for chunk in chunks if chunk.choices[0].delta.content]
    name = chunks[0].choices[0].delta.name

    assert "".join(texts) == "Hello"
    assert name == 'john'

    assert chunks[0].choices[0].delta.content == ''
    assert chunks[0].choices[0].delta.role == 'assistant'
    assert chunks[0].choices[0].delta.name == 'john'

    assert chunks[-1].choices[0].finish_reason == 'stop'


@pytest.mark.asyncio
@pytest.mark.parametrize("content_list", [
    ['**Hello** Wo', 'rl', 'd'],
    ['**Hello**', ' Wo', 'r', 'ld'],
])
async def test_buffered_chat_completion_wrapper_with_false_positives(tmp_path, content_list):
    wrapper = ChatCompletionWithUsername(mock_chat_completion_generator(content_list))

    chunks = [chunk async for chunk in wrapper]
    texts = [chunk.choices[0].delta.content for chunk in chunks if chunk.choices[0].delta.content]
    assert "".join(texts) == "**Hello** World"

    tokens_were_streamed = len(chunks) > 3
    assert tokens_were_streamed

    assert chunks[0].choices[0].delta.content == ''
    assert chunks[0].choices[0].delta.role == 'assistant'
    assert chunks[0].choices[0].delta.name is None

    assert chunks[-1].choices[0].finish_reason == 'stop'

# @pytest.mark.integration
# @pytest.mark.asyncio
# async def test_integration():
#     client = AsyncAnthropicOpenAIAdapter()
#     chat_completion = await client.chat.completions.create(
#         model="claude-3-haiku-20240307",
#         stream=True,
#         messages=[
#             {"role": "system", "content": "You're `john`, a math expert. Prefix your messages with **john>**"},
#             {"role": "user", "content": "**alice>** Short answer. 1 + 1=?"}
#         ]
#     )
#
#     received = []
#     async for resp in ChatCompletionWithUsername(chat_completion):
#         received += [resp]
#
#     assert received[0].model_dump()["choices"][0]["delta"]["role"] == "assistant"
#     assert received[0].model_dump()["choices"][0]["delta"]["name"] == "john"
#
#     tokens = [resp.model_dump()["choices"][0]["delta"]["content"] for resp in received]
#
#     content = ''.join(tokens[:-1])
#     assert 'john' not in content
#     assert tokens[0] == ''
#     assert '2' in tokens
#     assert tokens[-1] is None
