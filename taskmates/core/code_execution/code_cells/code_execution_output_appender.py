import base64
import os
from pathlib import Path


class CodeExecutionOutputAppender:
    @staticmethod
    def append_image_to_disk(base64_image, extension, code_cell_digest, chat_file_path):
        chat_dir = os.path.dirname(chat_file_path)
        attachments_dir = os.path.join(chat_dir, "attachments")
        os.makedirs(attachments_dir, exist_ok=True)

        image_path = os.path.join(attachments_dir, f"{code_cell_digest}.{extension}")
        image_data = base64.b64decode(base64_image)

        with open(image_path, "wb") as image_file:
            image_file.write(image_data)

        return Path(image_path).relative_to(chat_dir)
