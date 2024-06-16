import re

from typeguard import typechecked

from taskmates.formats.markdown.participants.parse_potential_mentions import parse_potential_mentions, MENTION_PATTERN


@typechecked
def parse_mention(content: str, participants: list[str]) -> str | None:
    mentions = parse_potential_mentions(content)
    usernames = [mention[1:] for mention in mentions]
    mentioned_assistants = [username for username in usernames
                            if username in participants]

    if not mentions:
        return None

    # Check if the message starts with @<username>
    if content.startswith(mentions[0]):
        return usernames[0]

    # Check if the content starts with "Hey @<username>" at the beginning of a paragraph
    for line in content.splitlines():
        if re.match(r"^Hey " + MENTION_PATTERN + r"\b", line):
            username = re.search(MENTION_PATTERN, line).group()[1:]
            return username

    if len(mentioned_assistants) == 1:
        return mentioned_assistants[0]
    elif len(mentioned_assistants) > 1:
        return usernames[-1]
    return None


def test_parse_mention_invite():
    content = "Hey @user1, Let's discuss the project."
    participants = ["user1", "user2"]
    assert parse_mention(content, participants) == "user1"


def test_parse_mention_invite_not_participant():
    content = "Hey @user3\nLet's discuss the project."
    participants = ["user1", "user2"]
    assert parse_mention(content, participants) == "user3"


def test_parse_mention_invite_multiple_lines():
    content = "Hey @user1, Let's discuss the project.\n@user2, what do you think?"
    participants = ["user1", "user2"]
    assert parse_mention(content, participants) == "user1"


def test_parse_mention_start_with_username():
    content = "@user1 Let's discuss the project."
    assert parse_mention(content, ["user2"]) == "user1"


def test_parse_mention_invite_not_at_beginning():
    content = "Let's discuss the project. Hey @user1, what do you think?"
    assert parse_mention(content, []) is None


def test_parse_mention_invite_middle_of_paragraph():
    content = "Let's discuss the project. Hey @user1, what do you think? @user2, any thoughts?"
    assert parse_mention(content, []) is None
