import re

import pyparsing as pp

def section_start_anchor():
    return pp.Regex(r"^(?=(\*\*|###### ))", re.MULTILINE)
