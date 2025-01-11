from typing import List, Dict, Optional

import pytest
import tiktoken

from taskmates.lib.openai_.model.chat_completion_chunk_model import ChatCompletionChunkModel
from taskmates.lib.openai_.model.choice_model import ChoiceModel
from taskmates.lib.openai_.model.delta_model import DeltaModel


class Quote:
    async def create(self,
                     model: str,
                     stream: bool,
                     messages: List[Dict[str, str]],
                     max_tokens=1024,
                     seed=None,
                     tools: Optional[List[Dict]] = None,
                     tool_choice: Optional[str] = None,
                     stop: Optional[List[str]] = None,
                     **kwargs):
        async def inner():
            # Simulate streaming response
            yield ChatCompletionChunkModel(
                id="mock_id",
                choices=[ChoiceModel(delta=DeltaModel(role="assistant", content=""))],
                created=None,
                model=model
            )

            content = messages[-1]["content"]
            content = '\n'.join('> ' + line for line in content.split('\n'))

            enc = tiktoken.encoding_for_model("gpt-4")
            encoded = enc.encode(content)
            tokens = []
            for token in encoded:
                tokens.append(enc.decode([token]))

            tokens.append("\n")
            tokens.append("\n")

            for token in tokens:
                yield ChatCompletionChunkModel(
                    id="mock_id",
                    choices=[ChoiceModel(delta=DeltaModel(content=token))],
                    created=None,
                    model=model
                )

            yield ChatCompletionChunkModel(
                id="mock_id",
                choices=[ChoiceModel(delta=DeltaModel(content=None), finish_reason="stop")],
                created=None,
                model=model
            )

        return inner()

    @property
    def chat(self):
        return type('Chat', (), {'completions': type('Completions', (), {'create': self.create})})()


@pytest.mark.asyncio
async def test_mock_client():
    client = Quote()
    chat_completion = await client.chat.completions.create(
        model="quote",
        stream=True,
        messages=[{"role": "user", "content": "Short answer. 1 + 1=?"}]
    )

    received = [chunk async for chunk in chat_completion]

    assert received[0].choices[0].delta.role == "assistant"
    assert received[0].choices[0].delta.content == ""

    tokens = [chunk.choices[0].delta.content
              for chunk in received
              if chunk.choices[0].delta.content is not None]
    assert ''.join(tokens).strip() == '> Short answer. 1 + 1=?'

    assert received[-1].choices[0].delta.content is None
    assert received[-1].choices[0].finish_reason == "stop"
