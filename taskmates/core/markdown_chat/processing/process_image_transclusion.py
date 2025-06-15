import os
from pathlib import Path

import pytest

from taskmates.core.markdown_chat.processing.extract_transclusion_links import extract_transclusion_links
from taskmates.lib.image_.encode_image import encode_image
from taskmates.lib.path_.is_image import is_image
from taskmates.lib.root_path.root_path import root_path


def render_image_transclusion(content, transclusions_base_dir):
    if not content:
        return content
    transclusion_links = extract_transclusion_links(content)
    if transclusion_links:
        content_parts = []
        for link in transclusion_links:
            if link.startswith("/"):
                filenames = [link]
            else:
                filenames = list(sorted(Path(transclusions_base_dir).glob(link)))
            if not filenames:
                raise ValueError(f"Transclusion link {link} not found")
            for filename in filenames:
                if os.path.isfile(filename):
                    file_extension = os.path.splitext(filename)[1].lower()
                    if is_image(filename):
                        content_parts.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{file_extension[1:]};base64,{encode_image(filename)}",
                                # "detail": "low",
                            },
                        })
                    else:
                        raise ValueError(f"File extension {file_extension} not supported")
        content_parts.insert(0, {
            "type": "text",
            "text": content
        })
        return content_parts
    else:
        return content


def test_with_image_transclusion(tmp_path):
    file_path = root_path() / "tests/fixtures/image.jpg"

    messages = [
        {
            "role": "user",
            "content": f"Hello\n![[{file_path}]]",
        }
    ]
    content = render_image_transclusion(messages[0]["content"], tmp_path)
    assert content[0]["type"] == "text"
    assert content[0]["text"] == f"Hello\n![[{file_path}]]"
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/jpg;base64,")


# def test_with_inline_image_transclusion(tmp_path):
#     file_path = root_path() / "tests/fixtures/image.jpg"
#
#     messages = [
#         {
#             "role": "user",
#             "content": f"Hello ![[{file_path}]]",
#         }
#     ]
#     content = render_image_transclusion(messages[0]["content"], tmp_path)
#     assert content[0]["type"] == "text"
#     assert content[0]["text"] == f"Hello ![[{file_path}]]"
#     assert content[1]["type"] == "image_url"
#     assert content[1]["image_url"]["url"].startswith("data:image/jpg;base64,")


def test_without_image_transclusion(tmp_path):
    temp_file = tmp_path / "text.txt"
    temp_file.write_text("Hello, world!\n")

    messages = [
        {
            "role": "user",
            "content": f"Hello\n![[{temp_file}]]\n",
        }
    ]

    with pytest.raises(ValueError):
        render_image_transclusion(messages[0]["content"], tmp_path)


