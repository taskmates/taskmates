import textwrap
from typing import Union

from markdown_tree_parser.parser import parse_string, Element


def parse_markdown_tree(obj: Union[str, Element]) -> dict:
    if isinstance(obj, str):
        return parse_markdown_tree(parse_string(obj))

    source = [{"level": obj.level,
               "content": obj.source,
               "full_source": obj.source,
               "text_source": obj.source}] if hasattr(obj, "source") else []
    main = [parse_markdown_tree(obj.main)] if hasattr(obj, "main") else []
    children = [parse_markdown_tree(i) for i in obj.children] if hasattr(obj, "children") else []
    consolidated_children = source + main + children
    parsed_markdown = dict(
        title=obj.title if hasattr(obj, "title") else None,
        text=obj.text if hasattr(obj, "text") else None,
        text_source=obj.text_source if hasattr(obj, "text_source") else None,
        level=obj.level if hasattr(obj, "level") else None,
        full_source=obj.full_source if hasattr(obj, "full_source") else None,
        children=consolidated_children
    )

    return parsed_markdown


def test_markdown_chat():
    text = """
    pretext
    
    # user
    1 + 1
    
    # assistant
    2
    
    # summary
    
    ## calculation
     
    1 + 1 = 2
    
    ## python
    
    ```python
    # summary
    print(1 + 1)
    ```
"""
    parsed_tree = parse_markdown_tree(textwrap.dedent(text))

    assert parsed_tree['level'] == 0
    assert parsed_tree['full_source'][:10] == '\npretext\n\n'

    children = [{"level": child['level'], "full_source": child['full_source'][0:10]} for child in
                parsed_tree['children']]
    assert children == [{'full_source': '\npretext\n', 'level': 0},
                        {'full_source': '# user\n1 +', 'level': 1},
                        {'full_source': '# assistan', 'level': 1},
                        {'full_source': '# summary\n', 'level': 1}] != [{'full_source': '# user\n1 +', 'level': 1},
                                                                        {'full_source': '# assistan', 'level': 1},
                                                                        {'full_source': '# summary\n', 'level': 1}]


def test_parse_markdown_with_only_title():
    text = "# Title"
    parsed_tree = parse_markdown_tree(textwrap.dedent(text))
    assert parsed_tree['level'] == 0
    assert parsed_tree['full_source'].startswith("# Title"[:10])


def test_parse_markdown_with_only_text():
    text = "Just some text without a title."
    parsed_tree = parse_markdown_tree(textwrap.dedent(text))
    assert parsed_tree['level'] == 0
    assert parsed_tree['full_source'] is None


def test_parse_markdown_with_nested_sections():
    text = """
    # Title
    ## Subtitle
    Content under subtitle
    """
    parsed_tree = parse_markdown_tree(textwrap.dedent(text))
    assert parsed_tree['level'] == 0
    assert parsed_tree['full_source'].startswith("\n# Title\n## Subtitle\nContent under subtitle\n"[:10])


def test_parse_markdown_missing_attributes():
    text = """
    # Title without text
    """
    parsed_tree = parse_markdown_tree(textwrap.dedent(text))
    assert parsed_tree['level'] == 0
    assert parsed_tree['full_source'].startswith("\n# Title without text\n"[:10])
