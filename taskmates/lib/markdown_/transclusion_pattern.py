import re

PATTERN = re.compile(r"^[#!](?:\[\[(.*)]]|\[.*]\((.*)\))$", re.MULTILINE)


def match_transclusion(content):
    found = re.search(PATTERN, content) or [None, None, None]
    return found[1] or found[2]


def test_pattern_wikilink_format():
    content = """# user
Source code:

#[[/Users/ralphus/Development/intellij/andre-ai-intellij-plugin/src/main/java/io/github/srizzo/andreai/ide/actions/AICompletionAction.java.chat/AICompletionAction.java.md]]
    """

    assert match_transclusion(
        content) == '/Users/ralphus/Development/intellij/andre-ai-intellij-plugin/src/main/java/io/github/srizzo/andreai/ide/actions/AICompletionAction.java.chat/AICompletionAction.java.md'


def test_pattern_mardown_format():
    content = """# user
Source code:

#[My Link](..%2F..%2Flink%2Fto%2Ffile)
    """

    assert match_transclusion(content) == '..%2F..%2Flink%2Fto%2Ffile'


def test_pattern_mardown_format_2():
    content = """# user
A cat:

![cat.jpeg](..%2F..%2F..%2F..%2F..%2FDownloads%2Fcat.jpeg)
    """

    assert match_transclusion(content) == '..%2F..%2F..%2F..%2F..%2FDownloads%2Fcat.jpeg'
