from typing import List, Optional

import pytest
import yaml
from jira import JIRA, Issue

from tools.jira_.get_issue_url import get_issue_url
from tools.jira_.get_jira_client import get_jira_client

"""
This module contains functions for interacting with JIRA.

Make all functions be async.

Write the corresponding unit tests in this file, not in a separate file.
"""


async def get_transition_id(jira: JIRA, issue: Issue, status: str) -> Optional[str]:
    """
    Get the transition ID for a given status.

    Args:
        jira (JIRA): A JIRA client instance.
        issue (Issue): A JIRA issue.
        status (str): The desired status.

    Returns:
        Optional[str]: The transition ID for the given status, or None if not found.
    """
    transitions = jira.transitions(issue)
    for transition in transitions:
        if transition['to']['name'] == status:
            return transition['id']
    return None


async def create_issue(summary: str, description: str, project: str, attachments: Optional[List[str]] = None,
                       status: str = "To Do",
                       parent: Optional[str] = None, depends_on: Optional[List[str]] = None,
                       issue_type: str = "Task",
                       custom_fields: Optional[dict] = None) -> str:
    """
    Create a new JIRA issue.

    Args:
        summary (str): The summary of the issue.
        description (str): The description of the issue.
        project (str): The JIRA project key.
        attachments (Optional[List[str]], optional): A list of file paths to attach to the issue. Defaults to None.
        status (str, optional): The initial status of the issue. Defaults to "To Do".
        parent (Optional[str], optional): The key of the parent issue. Defaults to None.
        depends_on (Optional[List[str]], optional): A list of issue keys that this issue depends on. Defaults to None.
        issue_type (str, optional): The issue type. Defaults to "Task".
        custom_fields (Optional[dict], optional): A dictionary of custom field IDs and their values. Defaults to None.

    Returns:
        str: A formatted string containing the issue key and URL.

    Raises:
        ValueError: If the provided status is invalid.
        :param issue_type:
        :param issue_type:
    """
    jira = get_jira_client()

    issue_dict = {
        'project': project,
        'summary': summary,
        'description': description,
        'issuetype': {'name': issue_type},
    }
    if parent:
        issue_dict['parent'] = {'key': parent}
    if depends_on:
        issue_dict['issuelinks'] = [{'type': {'name': 'Depends'}, 'outwardIssue': {'key': key}} for key in depends_on]
    if custom_fields:
        issue_dict.update(custom_fields)

    issue = jira.create_issue(fields=issue_dict)

    if attachments:
        for attachment in attachments:
            jira.add_attachment(issue=issue.key, attachment=str(attachment))

    if status != "To Do":
        transition_id = await get_transition_id(jira, issue, status)
        if transition_id:
            try:
                jira.transition_issue(issue, transition_id)
            except Exception as e:
                raise ValueError(f"Failed to transition issue to status '{status}': {str(e)}")
        else:
            raise ValueError(f"Invalid status: {status}")

    return f"Created issue {issue.key} - {get_issue_url(issue)}"


async def add_comment(issue_key: str, comment: str, attachments: Optional[List[str]] = None) -> str:
    """
    Add a comment to a JIRA issue.

    Args:
        issue_key (str): The key of the JIRA issue.
        comment (str): The comment text.
        attachments (Optional[List[str]], optional): A list of file paths to attach to the comment. Defaults to None.

    Returns:
        str: A formatted string containing the comment text and issue key.
    """
    jira = get_jira_client()
    issue = jira.issue(issue_key)
    comment = jira.add_comment(issue, comment)
    if attachments:
        for attachment in attachments:
            jira.add_attachment(issue=issue.key, attachment=str(attachment))
    return f"Added comment to {issue_key}: {comment.body}"


async def update_status(issue_key: str, status: str) -> str:
    """
    Update the status of a JIRA issue.

    Args:
        issue_key (str): The key of the JIRA issue.
        status (str): The new status.

    Returns:
        str: A formatted string containing the issue key and new status.

    Raises:
        ValueError: If the provided status is invalid.
    """
    jira = get_jira_client()
    issue = jira.issue(issue_key)
    transition_id = await get_transition_id(jira, issue, status)
    if transition_id:
        jira.transition_issue(issue, transition_id)
        return f"Updated status of {issue_key} to {status}"
    else:
        raise ValueError(f"Invalid status: {status}")


async def get_custom_field_id(field_name: str) -> str:
    """
    Get the ID of a custom field by its name.

    Args:
        field_name (str): The name of the custom field.

    Returns:
        str: The ID of the custom field.

    Raises:
        ValueError: If the custom field is not found.
    """
    custom_fields = await get_custom_fields()
    field_id = custom_fields.get(field_name)
    if field_id:
        return field_id
    else:
        raise ValueError(f"Custom field '{field_name}' not found")


async def search_issues(query: str) -> str:
    """
    List JIRA issues matching the provided JQL query.

    Args:
        query (str): A JQL query string.

    Returns:
        str: A formatted string containing the list of matching issues with additional fields, one issue per line.
    """
    jira = get_jira_client()
    goal_field_id = await get_custom_field_id('Goal')
    roadmap_field_id = await get_custom_field_id('Roadmap')
    category_field_id = await get_custom_field_id('Category')

    issues = jira.search_issues(query, fields='*all')

    def get_custom_field_value(field_value):
        if isinstance(field_value, list):
            return ", ".join(option.value for option in field_value)
        elif hasattr(field_value, 'value'):
            return field_value.value
        else:
            return str(field_value)

    def get_linked_issues(issue):
        links = []
        if issue.fields.issuelinks:
            for link in issue.fields.issuelinks:
                if hasattr(link, 'outwardIssue'):
                    links.append(f"{link.type.outward} {link.outwardIssue.key}")
                if hasattr(link, 'inwardIssue'):
                    links.append(f"{link.type.inward} {link.inwardIssue.key}")
        return ", ".join(links)

    issue_list = []
    for issue in issues:
        issue_str = f"{issue.key} - Summary: {getattr(issue.fields, 'summary', 'N/A')}, Status: {getattr(issue.fields, 'status', {}).name}, " \
                    f"Goal: {get_custom_field_value(getattr(issue.fields, goal_field_id, 'N/A'))}, " \
                    f"Roadmap: {get_custom_field_value(getattr(issue.fields, roadmap_field_id, 'N/A'))}, " \
                    f"Category: {get_custom_field_value(getattr(issue.fields, category_field_id, 'N/A'))}, " \
                    f"Assignee: {getattr(issue.fields.assignee, 'displayName', 'Unassigned') if issue.fields.assignee else 'Unassigned'}, " \
                    f"Linked Issues: {get_linked_issues(issue)}"
        issue_list.append(issue_str)

    if not issue_list:
        return "No matching issues found."

    return "Matching issues:\n" + "\n".join(issue_list)


async def delete_issues(issues: List[str]) -> str:
    """
    Delete multiple JIRA issues.

    Args:
        issues (List[str]): A list of JIRA issue keys to delete.

    Returns:
        str: A formatted string containing the list of deleted issues.
    """
    jira = get_jira_client()
    deleted_issues = []
    for issue_key in issues:
        issue = jira.issue(issue_key)
        issue.delete()
        deleted_issues.append(issue_key)
    return f"Deleted issues: {', '.join(deleted_issues)}"


async def get_custom_fields() -> dict:
    """
    Retrieve all custom fields from JIRA.

    Returns:
        dict: A dictionary mapping custom field names to their IDs.
    """
    jira = get_jira_client()
    fields = jira.fields()
    custom_fields = {}
    for field in fields:
        if field['custom']:
            custom_fields[field['name']] = field['id']
    return custom_fields


async def dump_context() -> str:
    """
    Retrieve the context information from JIRA and return it as a YAML string.

    Returns:
        str: A YAML string representing the context information.
    """
    jira = get_jira_client()

    # Retrieve all projects
    projects = jira.projects()

    context = {"projects": {}, "custom_fields": {}}

    for project in projects:
        project_key = project.key
        context["projects"][project_key] = {
            "name": project.name,
            "issue_types": [],
            "link_types": []
        }

        # Retrieve issue types for the project
        issue_types = jira.project(project_key).issueTypes
        for issue_type in issue_types:
            context["projects"][project_key]["issue_types"].append(issue_type.name)

        # Retrieve link types for the project
        link_types = jira.issue_link_types()
        for link_type in link_types:
            context["projects"][project_key]["link_types"].append(link_type.name)

    # Retrieve all custom fields
    custom_fields = await get_custom_fields()
    for field_name, field_id in custom_fields.items():
        context["custom_fields"][field_name] = field_id

    return yaml.dump(context)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_dump_context():
    context_yaml = await dump_context()
    assert isinstance(context_yaml, str)
    context = yaml.safe_load(context_yaml)
    assert context["projects"]["DEMO"] == {
        'name': 'Demo Project - IGNORE THIS PROJECT',
        'issue_types': [
            'Task',
            'Epic',
            'Subtask'],
        'link_types': [
            'Blocks',
            'Cloners',
            'Duplicate',
            'Jira Product Discovery datapoint issue link',
            'Jira Product Discovery issue link',
            'Jira Product Discovery merge issue link',
            'Relates']
    }
    assert 'custom_fields' in context
    assert 'Goal' in context['custom_fields']
    assert 'Roadmap' in context['custom_fields']
    assert 'Category' in context['custom_fields']


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_issue(tmp_path):
    summary = "Test issue from pytest"
    description = "This is a test issue created from pytest"
    attachment = tmp_path / "test.txt"
    attachment.write_text("This is a test attachment")
    project = "DEMO"

    result = await create_issue(summary, description, project, attachments=[str(attachment)])

    assert "Created issue" in result
    assert "https://upbits.atlassian.net/browse/" in result

    issue_key = result.split()[2]
    await update_status(issue_key, "In Progress")

    updated_issue = get_jira_client().issue(issue_key)
    assert updated_issue.fields.status.name == "In Progress"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_add_comment(tmp_path):
    summary = "Test issue for adding comment"
    description = "This is a test issue for adding comment"
    project = "DEMO"
    result = await create_issue(summary, description, project)
    issue_key = result.split()[2]

    comment_text = "This is a test comment"
    attachment = tmp_path / "test.txt"
    attachment.write_text("This is a test attachment")

    result = await add_comment(issue_key, comment_text, attachments=[str(attachment)])

    assert f"Added comment to {issue_key}" in result
    assert comment_text in result


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_status():
    summary = "Test issue for updating status"
    description = "This is a test issue for updating status"
    project = "DEMO"
    result = await create_issue(summary, description, project)
    issue_key = result.split()[2]

    result = await update_status(issue_key, "Done")

    assert f"Updated status of {issue_key} to Done" in result


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_issues():
    project = "DEMODIS"
    summary1 = "Test search issue with fields 1"
    summary2 = "Test search issue with fields 2"
    goal_value = "Learn this tool"
    roadmap_value = "Now"
    category_value = "Sample ideas"

    goal_field_id = await get_custom_field_id('Goal')
    roadmap_field_id = await get_custom_field_id('Roadmap')
    category_field_id = await get_custom_field_id('Category')

    custom_fields = {
        goal_field_id: [{"value": goal_value}],
        roadmap_field_id: {"value": roadmap_value},
        category_field_id: {"value": category_value}
    }

    issue1 = await create_issue(summary1, "Test search issue", project, status="Discovery",
                                issue_type='Idea',
                                custom_fields=custom_fields)
    issue2 = await create_issue(summary2, "Test search issue", project, status="Done",
                                issue_type='Idea',
                                custom_fields=custom_fields)

    issue_key1 = issue1.split()[2]
    issue_key2 = issue2.split()[2]

    query = 'summary ~ "Test search issue with fields" AND project = \'DEMODIS\' AND status = \'Discovery\''
    result = await search_issues(query)

    assert "DEMODIS" in result
    assert "Test search issue with fields 1" in result
    assert "Status: Discovery" in result
    assert "Goal: Learn this tool" in result
    assert "Roadmap: Now" in result
    assert "Category: Sample ideas" in result

    await delete_issues([issue_key1, issue_key2])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_delete_issues():
    project = "DEMO"
    summary1 = "Test issue for deletion 1"
    summary2 = "Test issue for deletion 2"
    result1 = await create_issue(summary1, "Test issue for deletion", project)
    result2 = await create_issue(summary2, "Test issue for deletion", project)
    issue_key1 = result1.split()[2]
    issue_key2 = result2.split()[2]

    result = await delete_issues([issue_key1, issue_key2])

    assert f"Deleted issues: {issue_key1}, {issue_key2}" in result
    with pytest.raises(Exception):
        get_jira_client().issue(issue_key1)
    with pytest.raises(Exception):
        get_jira_client().issue(issue_key2)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_dump_context():
    context_yaml = await dump_context()
    assert isinstance(context_yaml, str)
    context = yaml.safe_load(context_yaml)
    assert context["projects"]["DEMO"] == {
        'name': 'Demo Project - IGNORE THIS PROJECT',
        'issue_types': [
            'Task',
            'Epic',
            'Subtask'],
        'link_types': [
            'Blocks',
            'Cloners',
            'Duplicate',
            'Jira Product Discovery datapoint issue link',
            'Jira Product Discovery issue link',
            'Jira Product Discovery merge issue link',
            'Relates']
    }


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_custom_fields():
    custom_fields = await get_custom_fields()
    assert 'Goal' in custom_fields
    assert 'Roadmap' in custom_fields
    assert 'Category' in custom_fields


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_custom_field_id():
    goal_field_id = await get_custom_field_id('Goal')
    assert goal_field_id is not None

    with pytest.raises(ValueError):
        await get_custom_field_id('NonExistentField')

async def read_issue(issue_key: str) -> str:
    """
    Fetch all details of a JIRA issue, including attachments and comments.

    Args:
        issue_key (str): The key of the JIRA issue.

    Returns:
        str: A formatted string containing the issue details, attachments, and comments.
    """
    jira = get_jira_client()
    issue = jira.issue(issue_key)

    # Fetch issue details
    issue_details = f"Issue Key: {issue.key}\n"
    issue_details += f"Summary: {issue.fields.summary}\n"
    issue_details += f"Description: {issue.fields.description}\n"
    issue_details += f"Status: {issue.fields.status.name}\n"
    issue_details += f"Assignee: {issue.fields.assignee.displayName if issue.fields.assignee else 'Unassigned'}\n"

    # Fetch attachments
    attachments = []
    for attachment in issue.fields.attachment:
        attachments.append(f"{attachment.filename} - {attachment.content}")
    if attachments:
        issue_details += f"Attachments:\n{chr(10).join(attachments)}\n"
    else:
        issue_details += "Attachments: None\n"

    # Fetch comments
    comments = []
    for comment in issue.fields.comment.comments:
        comments.append(f"{comment.author.displayName}: {comment.body}")
    if comments:
        issue_details += f"Comments:\n{chr(10).join(comments)}\n"
    else:
        issue_details += "Comments: None\n"

    return issue_details


@pytest.mark.integration
@pytest.mark.asyncio
async def test_read_issue(tmp_path):
    # Create a test issue
    summary = "Test issue for read_issue"
    description = "This is a test issue for read_issue function"
    project = "DEMO"
    attachment = tmp_path / "test.txt"
    attachment.write_text("This is a test attachment")
    result = await create_issue(summary, description, project, attachments=[str(attachment)])
    issue_key = result.split()[2]

    # Add a comment to the test issue
    comment_text = "This is a test comment"
    await add_comment(issue_key, comment_text)

    # Fetch issue details
    issue_details = await read_issue(issue_key)

    # Assert issue details
    assert f"Issue Key: {issue_key}" in issue_details
    assert f"Summary: {summary}" in issue_details
    assert f"Description: {description}" in issue_details
    assert "Status: To Do" in issue_details
    assert "Attachments:" in issue_details
    assert "test.txt" in issue_details
    assert "Comments:" in issue_details
    assert comment_text in issue_details

    # Clean up the test issue
    await delete_issues([issue_key])
