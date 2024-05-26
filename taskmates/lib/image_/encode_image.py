import base64
from io import BytesIO

from PIL import Image


def encode_image(image_path):
    with Image.open(image_path) as img:
        original_format = img.format  # Detect the original image format

        # Calculate the height using the aspect ratio
        aspect_ratio = img.height / img.width
        new_height = int(768 * aspect_ratio)

        # Resize the image while maintaining the aspect ratio
        img = img.resize((768, new_height), Image.Resampling.LANCZOS)

        # Save the image to a bytes buffer, keeping the original format
        with BytesIO() as buffer:
            img.save(buffer, format=original_format)
            buffer.seek(0)
            image_data = buffer.read()

        # Encode the image data
        return base64.b64encode(image_data).decode('utf-8')
