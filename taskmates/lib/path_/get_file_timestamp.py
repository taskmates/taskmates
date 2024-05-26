import os
from pathlib import Path


def get_file_timestamp(file_path: Path) -> str:
    modification_time_float = os.path.getmtime(file_path)
    modification_time_int = int(modification_time_float)

    return str(modification_time_int)
