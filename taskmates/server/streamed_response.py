import json
from typing import Union

from openai.types.chat import ChatCompletionChunk
from taskmates.lib.openai_.model.chat_completion_chunk_model import ChatCompletionChunkModel
from typeguard import typechecked



class StreamedResponse:
    def __init__(self):
        self.final_json = {}
        self.current_tool_call_id = None
        self.tool_calls_by_id = {}
        self.content_delta = ''
        self.choices = []
        self.finish_reason = None

    @typechecked
    async def accept(self, chat_completion_chunk: Union[ChatCompletionChunk, ChatCompletionChunkModel]):
        chat_completion_chunk_dict = chat_completion_chunk.model_dump()
        delta = chat_completion_chunk_dict.get('choices', [{}])[0].get('delta', {})
        tool_calls = delta.get('tool_calls', []) or []
        content = delta.get('content', '')

        for tool_call in tool_calls:
            tool_call_id = tool_call.get('id', None)
            arguments = tool_call['function'].get('arguments', '')

            if tool_call_id:
                self.current_tool_call_id = tool_call_id
                self.tool_calls_by_id[self.current_tool_call_id] = {
                    'id': tool_call_id,
                    'function': {
                        'name': tool_call['function'].get('name', None),
                        'arguments': ''
                    },
                    'type': 'function'
                }

            if arguments is not None:
                self.tool_calls_by_id[self.current_tool_call_id]['function']['arguments'] += arguments

        if content is not None:
            self.content_delta += content

        # Remove the choices field from data and update final_json
        if 'choices' in chat_completion_chunk_dict:
            del chat_completion_chunk_dict['choices']
        self.final_json.update(chat_completion_chunk_dict)

    @property
    def payload(self):
        if self.tool_calls_by_id or self.content_delta:
            message = {
                'role': 'assistant',
                'content': self.content_delta if self.content_delta else None,
            }
            if self.tool_calls_by_id:
                message['tool_calls'] = list(self.tool_calls_by_id.values())
            self.choices.append({
                'index': 0,
                'message': message,
                'finish_reason': 'tool_calls' if self.tool_calls_by_id else 'stop'
            })

        # Add the combined choices to the final_json
        self.final_json['choices'] = self.choices

        # Change the object type to "chat.completion"
        self.final_json['object'] = 'chat.completion'

        return self.final_json

# TODO
# def test_reassemble_content():
#     reassembler = StreamedResponse()
#     # Read JSON lines from the file
#     for line in (root_path() / "lib/openai_/response" / 'content_stream_example.jsonl').read_text().splitlines():
#         reassembler.accept(json.loads(line))
#     expected = json.loads((root_path() / "lib/openai_/response" / 'content_payload_example.json').read_text())
#     assert reassembler.payload == expected

# TODO
# def test_reassemble_tool_calls():
#     reassembler = StreamedResponse()
#     # Read JSON lines from the file
#     for line in (root_path() / "lib/openai_/response" / 'tool_calls_stream_example.jsonl').read_text().splitlines():
#         reassembler.accept(json.loads(line))
#     expected = json.loads((root_path() / "lib/openai_/response" / 'tool_calls_payload_example.json').read_text())
#     expected.pop('usage')
#     assert reassembler.payload == expected
