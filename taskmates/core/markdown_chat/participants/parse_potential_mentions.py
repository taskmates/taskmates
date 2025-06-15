import re

import pytest

MENTION_PATTERN = r"(?<!\w)@\w+"


def parse_potential_mentions(content):
    unique_mentions = []
    matches = re.findall(MENTION_PATTERN, content)
    for match in matches:
        if match not in unique_mentions:
            unique_mentions.append(match)
    return unique_mentions


# Test when a single mention is present
def test_parse_single_mention():
    content = "Hello @user, how are you?"
    expected_mentions = ["@user"]
    assert parse_potential_mentions(content) == expected_mentions


# Test when multiple mentions are present
def test_parse_multiple_mentions():
    content = "Hi @user1, please meet @user2."
    expected_mentions = ["@user1", "@user2"]
    assert parse_potential_mentions(content) == expected_mentions


# Test when no mentions are present
def test_parse_no_mentions():
    content = "Hello there, how are you?"
    assert parse_potential_mentions(content) == []


# Test when the mention is part of a word
def test_parse_mention_part_of_word():
    content = "Hello there, how are you doing@today?"
    assert parse_potential_mentions(content) == []


# Test when the mention has special characters
def test_parse_mention_with_special_chars():
    content = "Hello @user!, how are you?"
    assert parse_potential_mentions(content) == ["@user"]


# Test when the mention is at the start of the content
def test_parse_mention_at_start():
    content = "@user, welcome!"
    expected_mentions = ["@user"]
    assert parse_potential_mentions(content) == expected_mentions


# Test when the mention is at the end of the content
def test_parse_mention_at_end():
    content = "Welcome, @user"
    expected_mentions = ["@user"]
    assert parse_potential_mentions(content) == expected_mentions


# Test when the content is empty
def test_parse_empty_content():
    content = ""
    assert parse_potential_mentions(content) == []


# Test when the content == []
def test_parse_none_content():
    content = None
    with pytest.raises(TypeError):
        parse_potential_mentions(content)


# Test when the content has a mention with underscores
def test_parse_mention_with_underscores():
    content = "Hello @_user_name_, how are you?"
    expected_mentions = ["@_user_name_"]
    assert parse_potential_mentions(content) == expected_mentions


# Test when the content has a mention with numbers
def test_parse_mention_with_numbers():
    content = "Hello @user123, how are you?"
    expected_mentions = ["@user123"]
    assert parse_potential_mentions(content) == expected_mentions
