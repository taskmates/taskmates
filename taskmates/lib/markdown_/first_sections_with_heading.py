import textwrap

from taskmates.lib.markdown_.parse_markdown_tree import parse_markdown_tree


def first_sections_with_heading(markdown, heading):
    parsed_tree = parse_markdown_tree(markdown)

    found = []

    if parsed_tree.get("main", {}).get("text_source") == heading:
        found.append(parsed_tree["main"])

    for child in parsed_tree["children"]:
        if child["text_source"] == heading:
            found.append(child)
    if not found:
        raise ValueError(f"Could not find heading {heading} in {parsed_tree}")
    return found


def test_find_main_heading():
    text = """
    # my heading
    my content
    """
    heading = "# my heading"
    expected_full_source = "# my heading\nmy content\n"
    found = first_sections_with_heading(textwrap.dedent(text), heading)
    assert found[0]["full_source"] == expected_full_source


def test_find_heading():
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
    # print(json.dumps(parsed_tree, indent=4, ensure_ascii=False))

    heading = "# summary"
    expected_full_source = "# summary\n\n## calculation\n\n1 + 1 = 2\n\n## python\n\n```python\n# summary\nprint(1 + 1)\n```\n"

    found = first_sections_with_heading(textwrap.dedent(text), heading)

    assert found[0]["full_source"] == expected_full_source
