import re
from typing import Tuple, Dict

import yaml

FRONTMATTER_PATTERN = r'^---\n(.+?)\n---'


def parse_front_matter_and_content(content: str) -> Tuple[Dict[str, any], str]:
    # Check for front_matter
    front_matter = {}
    front_matter_match = re.match(FRONTMATTER_PATTERN, content, re.DOTALL)
    if front_matter_match:
        # Extract and parse front_matter
        front_matter_content = front_matter_match.group(1)
        front_matter = yaml.safe_load(front_matter_content)
        # Remove front_matter from content
        content = content[front_matter_match.end():].lstrip('\n')
    return front_matter, content
