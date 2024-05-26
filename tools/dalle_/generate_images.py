import base64
import os
import textwrap
from pathlib import Path
from typing import Literal, Optional

from openai import AsyncOpenAI
from typeguard import typechecked


async def main():
    # set the prompt
    generation_response = await generate_images(
        prompt="minimalist SVG color icons of a wide variety of vegetables and fruits",
        quality="hd",
        style="natural")

    # print response
    print(generation_response)


async def generate_images(prompt: str,
                          quality: Literal["standard", "hd"] = "hd",
                          size: Literal["1024x1024", "1024x1792", "1792x1024"] = "1024x1024",
                          style: Optional[Literal["vivid", "natural"]] = "vivid") -> str:
    """
    Generates images based on a text description using specified parameters.

    :param prompt: A text description of the desired image(s). Don't write instructions, write the description of the desired result. The maximum length is 1000 characters for dall-e-2 and 4000 characters for dall-e-3.
    :param quality: The quality of the image that will be generated. Must be one of "standard" or "hd". "hd" creates images with finer details and greater consistency across the image. This param is only supported for dall-e-3. Defaults to "hd".
    :param size: The size of the generated images. Must be one of "1024x1024", "1792x1024", or "1024x1792" for dall-e-3 models. Defaults to "1024x1024".
    :param style: The style of the generated images. Must be one of "vivid" or "natural". "vivid" causes the model to lean towards generating hyper-real and dramatic images. "natural" causes the model to produce more natural, less hyper-real looking images. Defaults to "vivid".
    """

    client = AsyncOpenAI()

    generation_response = await client.images.generate(
        model="dall-e-3",
        quality=quality,
        style=style,
        prompt=prompt,
        size=size,
        response_format="b64_json",
    )

    image_responses = []
    for i, image_data in enumerate(generation_response.model_dump()["data"]):
        code_cell_id = str(generation_response.model_dump()['created']) + f'-{i}'
        chat_dir = Path(os.environ.get("CHAT_DIR", Path.cwd()))
        image_path = append_image_to_disk(image_data['b64_json'], "png", code_cell_id, chat_dir)

        if image_data.get('revised_prompt'):
            image_responses.append(textwrap.dedent(f"""\
            Revised Prompt: {image_data['revised_prompt']}
            
            - Generated Image [{i + 1}] at: {image_path}
            """))
        else:
            image_responses.append(textwrap.dedent(f"""\
            - Generated Image [{i + 1}] at: {image_path}
            """))

    return "\n\n".join(image_responses)


@typechecked
def append_image_to_disk(base64_image: str, extension: str, code_cell_id: str, chat_file_dir: Path) -> str:
    image_bytes = base64.b64decode(base64_image)
    attachments_dir = chat_file_dir / "attachments"
    try:
        os.makedirs(attachments_dir, exist_ok=True)
        image_path = attachments_dir / f"{code_cell_id}.{extension}"
        with open(image_path, "wb") as file:
            file.write(image_bytes)
        return str(image_path.relative_to(chat_file_dir))
    except IOError as e:
        raise RuntimeError(str(e))


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
