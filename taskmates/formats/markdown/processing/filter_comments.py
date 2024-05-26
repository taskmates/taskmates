import re


def filter_comments(content):
    return re.sub(r'^(- )?\[//]: # \(.*?\n', '', content, flags=re.MULTILINE)


def test_filter_comments():
    content = """
# system
- go_to_url
- scroll
- click
- type
- enter
- [//]: # (- list item comment)
[//]: # (regular comment)
You are an agent controlling a browser    
    """
    assert filter_comments(content) == """
# system
- go_to_url
- scroll
- click
- type
- enter
You are an agent controlling a browser    
    """

