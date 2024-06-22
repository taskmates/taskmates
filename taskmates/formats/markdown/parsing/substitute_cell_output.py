import re

from typeguard import typechecked


@typechecked
def substitute_cell_output(content: str) -> str:
    return re.sub(r'^(###### Cell Output: .*)$', lambda
        match: f'**submessage {{"name": "cell_output", "role": "user"}}**\n{match.group(1)}',
                  content,
                  flags=re.MULTILINE)
