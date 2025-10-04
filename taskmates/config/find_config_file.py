from pathlib import Path
from typing import List, Union, Optional

from taskmates.lib.root_path.root_path import root_path


def find_config_file(config_name: str, base_dirs: List[Union[str, Path]]) -> Optional[Path]:
    for taskmates_dir in [*base_dirs, root_path() / "taskmates" / "defaults"]:
        config_path = Path(taskmates_dir) / config_name
        if config_path.exists():
            return config_path

    return None
