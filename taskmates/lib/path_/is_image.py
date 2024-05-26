import os

from taskmates.lib.path_.is_binary_file import is_binary_file


def is_image(file_path):
    file_extension = os.path.splitext(file_path)[1]
    return file_extension.lower() in ['.jpg', '.jpeg', '.png'] and is_binary_file(file_path)
