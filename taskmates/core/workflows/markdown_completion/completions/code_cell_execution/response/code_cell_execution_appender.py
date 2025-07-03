import json
from pathlib import Path

from nbconvert.filters import strip_ansi
from typeguard import typechecked

from taskmates.core.workflows.markdown_completion.completions.code_cell_execution.code_execution_output_appender import CodeExecutionOutputAppender
from taskmates.core.workflows.markdown_completion.completions.code_cell_execution.execution.code_execution import CodeExecution
from taskmates.core.workflows.signals.markdown_completion_signals import MarkdownCompletionSignals


@typechecked
class CodeCellExecutionAppender:
    def __init__(self, project_dir, chat_file,
                 markdown_completion_signals: MarkdownCompletionSignals):
        self.state = {}
        self.project_dir = project_dir
        self.chat_file: Path = Path(chat_file)
        self.markdown_completion_signals = markdown_completion_signals
        self.appended_completions = []
        self.processed_code_cells = set()

    async def process_code_cell_output(self, code_cell_chunk):
        msg = code_cell_chunk['msg']
        # print("processing msg:", msg["msg_type"], flush=True)

        msg_id = code_cell_chunk["msg"]["parent_header"]["msg_id"]
        self.processed_code_cells.add(msg_id)
        code_cell_id = f"cell_{len(self.processed_code_cells) - 1}"

        msg_type = msg['msg_type']
        content = msg['content']

        # TODO: Remove this when the issue is fixed
        if "Exception in callback BaseAsyncIOLoop._handle_events" in json.dumps(content):
            return

        output = {
            "msg_id": code_cell_chunk['msg_id'],
            "source": code_cell_chunk['cell_source'],
            "output_type": msg_type,
            "name": "",
            "mime_type": None,
            "text": ""
        }

        if msg_type in ('execute_input', 'execution_state', 'status', 'clear_output'):
            return

        if msg_type == 'stream':
            output["name"] = content['name']
            output["mime_type"] = "text"
            output["text"] = content['text']
        elif msg_type == 'execute_result':
            data = content['data']
            for key, value in data.items():
                output["name"] = key.replace("text/", "")
                output["mime_type"] = key
                output["text"] = value
        elif msg_type == 'error':
            output["name"] = "error"
            output["mime_type"] = "text/plain"
            ename = content['ename']
            evalue = content['evalue']
            traceback = list(map(strip_ansi, content["traceback"]))
            formatted_traceback = "\n".join(traceback) + "\n"
            error_message = f"{ename}: {evalue}"
            if error_message in formatted_traceback:
                output["text"] = formatted_traceback
            else:
                output["text"] = error_message + "\n" + formatted_traceback
        elif msg_type == 'display_data':
            display_data = content['data']
            image_mime_type = None
            base64_image = None

            output["name"] = "display"
            output["mime_type"] = "text/plain"

            for key, value in display_data.items():
                if key == "text/plain":
                    output["name"] = value
                elif key.startswith("image/"):
                    image_mime_type = key
                    base64_image = value

            if base64_image:
                extension = image_mime_type.split("/")[1]
                code_cell_digest = CodeExecution.generate_code_cell_id(output["source"])
                image_path = CodeExecutionOutputAppender.append_image_to_disk(
                    base64_image=base64_image,
                    extension=extension,
                    code_cell_digest=code_cell_digest,
                    chat_file_path=str(self.chat_file)
                )
                output["mime_type"] = "text/markdown"
                output["text"] = f"![{output['name']}]({image_path})"
        else:
            output["name"] = msg_type
            output["mime_type"] = "text/plain"
            output["text"] = json.dumps(content)

        await self.maybe_append_execution_output(code_cell_id, output["name"], output["mime_type"], output["text"])

    async def process_code_cells_completed(self):
        previous_mime_type = self.state.get("previousMimeType")
        was_preformatted = previous_mime_type and previous_mime_type not in ["text/html", "text/markdown"]
        was_empty = not self.appended_completions

        if not self.appended_completions:
            await self.maybe_append_execution_output("cell_0",
                                                     "stdout",
                                                     "text/html",
                                                     "")

        execution_footer = CodeExecution.format_code_cell_output_footer(was_preformatted, was_empty)
        await self.append(execution_footer)

    @typechecked
    async def maybe_append_execution_output(self, code_cell_id: str, section_name: str, mime_type: str, output):
        previous_code_cell_id = self.state.get("previousCodeCellId")
        previous_section = self.state.get("previousSection")
        previous_mime_type = self.state.get("previousMimeType")
        is_first_section = previous_section is None
        has_section_changed = section_name != previous_section or code_cell_id != previous_code_cell_id
        is_preformatted = mime_type not in ["text/html", "text/markdown"]
        was_preformatted = previous_mime_type and previous_mime_type not in ["text/html", "text/markdown"]

        if has_section_changed:
            if not is_first_section:
                await self.append(CodeExecution.format_code_cell_output_footer(was_preformatted, False))
            await self.append(CodeExecution.format_code_cell_output_header(section_name, code_cell_id, is_preformatted))

        await self.append(CodeExecution.format_code_cell_output(output, is_preformatted))
        self.state["previousCodeCellId"] = code_cell_id
        self.state["previousSection"] = section_name
        self.state["previousMimeType"] = mime_type

    async def append(self, text):
        self.appended_completions.append(text)
        await self.markdown_completion_signals.response.send_async(text)
