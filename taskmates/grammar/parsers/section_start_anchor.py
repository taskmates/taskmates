import re

import pyparsing as pp

POTENTIAL_SECTION_START_REGEX = r"^(?=(\*\*|###### ))"


def section_start_anchor():
    return pp.Regex(POTENTIAL_SECTION_START_REGEX, re.MULTILINE).suppress()
