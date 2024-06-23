import re
from typing import AsyncIterable, List

import pytest
from taskmates.assistances.chat_completion.openai_adapters.anthropic_openai_adapter.anthropic_openai_adapter import \
    AsyncAnthropicOpenAIAdapter
from taskmates.lib.openai_.model.chat_completion_chunk_model import ChatCompletionChunkModel
from taskmates.lib.openai_.model.choice_model import ChoiceModel
from taskmates.lib.openai_.model.delta_model import DeltaModel


class ChatCompletionWithUsername:
    def __init__(self, chat_completion: AsyncIterable[ChatCompletionChunkModel]):
        self.chat_completion = chat_completion
        self.buffered_tokens: List[str] = []
        self.name = None

    async def __aiter__(self):
        async for chunk in self.chat_completion:
            if chunk.choices[0].delta.content is None:
                yield chunk
                continue

            content = chunk.choices[0].delta.content
            self.buffered_tokens.append(content)

            buffered_content = "".join(self.buffered_tokens)

            # yield the initial chunk, after confirming there's no username
            if len(self.buffered_tokens) == 2 and buffered_content[:2] != '**':
                yield self._create_chunk(chunk, '', 'assistant', None)
                yield chunk
                continue

            # yield the initial chunk, when completing the username
            match_username = re.match(r'^\*\*([^*]+)>\*\*:?$', buffered_content)
            if match_username:
                self.name = match_username.group(1) if match_username else None
                yield self._create_chunk(chunk, '', 'assistant', self.name)
                continue

            # yield the initial chunk after completing the username, removing any space prefix
            previous_text = "".join(self.buffered_tokens[:-1])
            previously_matched_username = re.match(r'^\*\*([^*]+)>\*\*:?$', previous_text)
            if previously_matched_username:
                if content[1:] != '':
                    yield self._create_chunk(chunk, content[1:], None, None)
                continue

            # buffer incomplete username
            if buffered_content == '' or re.match(r'^\*\*[^*]*?$', buffered_content):
                continue

            yield chunk

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


@pytest.mark.asyncio
async def test_buffered_chat_completion_wrapper(tmp_path):
    async def mock_chat_completion():
        yield ChatCompletionChunkModel(
            choices=[ChoiceModel(delta=DeltaModel(role='assistant', content=''))],
            model='mock_model'
        )
        yield ChatCompletionChunkModel(
            choices=[ChoiceModel(delta=DeltaModel(content='He'))],
            model='mock_model'
        )
        yield ChatCompletionChunkModel(
            choices=[ChoiceModel(delta=DeltaModel(content='llo'))],
            model='mock_model'
        )
        yield ChatCompletionChunkModel(
            choices=[ChoiceModel(delta=DeltaModel(content=None), finish_reason='stop')],
            model='mock_model'
        )

    # Create an instance of ChatCompletionWithUsername
    wrapper = ChatCompletionWithUsername(mock_chat_completion())

    # Collect the chunks from the wrapper
    chunks = [chunk async for chunk in wrapper]

    # Assert the expected behavior
    assert chunks[0].choices[0].delta.content == ''
    assert chunks[0].choices[0].delta.role == 'assistant'
    assert chunks[0].choices[0].delta.name is None
    assert chunks[1].choices[0].delta.content == 'He'
    assert chunks[2].choices[0].delta.content == 'llo'
    assert chunks[3].choices[0].delta.content is None
    assert chunks[3].choices[0].finish_reason == 'stop'


@pytest.mark.asyncio
async def test_buffered_chat_completion_wrapper_with_username(tmp_path):
    async def mock_chat_completion_with_username():
        yield ChatCompletionChunkModel(
            choices=[ChoiceModel(delta=DeltaModel(role='assistant', content=''))],
            model='mock_model'
        )
        yield ChatCompletionChunkModel(
            choices=[ChoiceModel(delta=DeltaModel(content='**'))],
            model='mock_model'
        )
        yield ChatCompletionChunkModel(
            choices=[ChoiceModel(delta=DeltaModel(content='jo'))],
            model='mock_model'
        )
        yield ChatCompletionChunkModel(
            choices=[ChoiceModel(delta=DeltaModel(content='hn>'))],
            model='mock_model'
        )
        yield ChatCompletionChunkModel(
            choices=[ChoiceModel(delta=DeltaModel(content='**'))],
            model='mock_model'
        )
        yield ChatCompletionChunkModel(
            choices=[ChoiceModel(delta=DeltaModel(content=' '))],
            model='mock_model'
        )
        yield ChatCompletionChunkModel(
            choices=[ChoiceModel(delta=DeltaModel(content='He'))],
            model='mock_model'
        )
        yield ChatCompletionChunkModel(
            choices=[ChoiceModel(delta=DeltaModel(content='llo'))],
            model='mock_model'
        )
        yield ChatCompletionChunkModel(
            choices=[ChoiceModel(delta=DeltaModel(content=None), finish_reason='stop')],
            model='mock_model'
        )

    # Create an instance of ChatCompletionWithUsername
    wrapper = ChatCompletionWithUsername(mock_chat_completion_with_username())

    # Collect the chunks from the wrapper
    chunks = [chunk async for chunk in wrapper]

    texts = [chunk.choices[0].delta.content for chunk in chunks]
    names = [chunk.choices[0].delta.name for chunk in chunks]

    assert texts == ['', 'He', 'llo', None]
    assert names == ['john', None, None, None]

    assert chunks[0].choices[0].delta.content == ''
    assert chunks[0].choices[0].delta.role == 'assistant'
    assert chunks[0].choices[0].delta.name == 'john'

    assert chunks[-1].choices[0].finish_reason == 'stop'


@pytest.mark.asyncio
async def test_buffered_chat_completion_wrapper_with_username_and_trimming_initial_space(tmp_path):
    async def mock_chat_completion_with_username():
        yield ChatCompletionChunkModel(
            choices=[ChoiceModel(delta=DeltaModel(role='assistant', content=''))],
            model='mock_model'
        )
        yield ChatCompletionChunkModel(
            choices=[ChoiceModel(delta=DeltaModel(content='**'))],
            model='mock_model'
        )
        yield ChatCompletionChunkModel(
            choices=[ChoiceModel(delta=DeltaModel(content='jo'))],
            model='mock_model'
        )
        yield ChatCompletionChunkModel(
            choices=[ChoiceModel(delta=DeltaModel(content='hn>'))],
            model='mock_model'
        )
        yield ChatCompletionChunkModel(
            choices=[ChoiceModel(delta=DeltaModel(content='**'))],
            model='mock_model'
        )
        yield ChatCompletionChunkModel(
            choices=[ChoiceModel(delta=DeltaModel(content=' He'))],
            model='mock_model'
        )
        yield ChatCompletionChunkModel(
            choices=[ChoiceModel(delta=DeltaModel(content='llo'))],
            model='mock_model'
        )
        yield ChatCompletionChunkModel(
            choices=[ChoiceModel(delta=DeltaModel(content=None), finish_reason='stop')],
            model='mock_model'
        )

    # Create an instance of ChatCompletionWithUsername
    wrapper = ChatCompletionWithUsername(mock_chat_completion_with_username())

    # Collect the chunks from the wrapper
    chunks = [chunk async for chunk in wrapper]

    texts = [chunk.choices[0].delta.content for chunk in chunks]
    names = [chunk.choices[0].delta.name for chunk in chunks]

    assert texts == ['', 'He', 'llo', None]
    assert names == ['john', None, None, None]

    assert chunks[0].choices[0].delta.content == ''
    assert chunks[0].choices[0].delta.role == 'assistant'
    assert chunks[0].choices[0].delta.name == 'john'

    assert chunks[-1].choices[0].finish_reason == 'stop'


@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration():
    client = AsyncAnthropicOpenAIAdapter()
    chat_completion = await client.chat.completions.create(
        model="claude-3-sonnet-20240229",
        stream=True,
        messages=[
            {"role": "system", "content": "You're `john`, a math expert. Prefix your messages with **john>**"},
            {"role": "user", "content": "**alice>** Short answer. 1 + 1=?"}
        ]
    )

    received = []
    async for resp in ChatCompletionWithUsername(chat_completion):
        received += [resp]

    assert received[0].model_dump()["choices"][0]["delta"]["role"] == "assistant"
    assert received[0].model_dump()["choices"][0]["delta"]["name"] == "john"

    tokens = [resp.model_dump()["choices"][0]["delta"]["content"] for resp in received]

    content = ''.join(tokens[:-1])
    assert 'john' not in content
    assert tokens[0] == ''
    assert '2' in tokens
    assert tokens[-1] is None
