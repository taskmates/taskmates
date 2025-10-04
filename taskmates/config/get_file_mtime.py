import os


def get_file_mtime(file_path):
    return os.path.getmtime(file_path) if file_path and os.path.exists(file_path) else None
