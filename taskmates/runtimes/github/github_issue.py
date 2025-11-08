# import os
#
# from taskmates.extensions.actions.get_github_app_installation_token import GithubAppInstallationToken
# from taskmates.core.workflow_engine.fulfills import fulfills
# from taskmates.core.workflow_engine.workflow import Workflow
# from taskmates.runtimes.github.compose_chat_from_github_issue import \
#     compose_chat_from_github_issue
# from taskmates.runtimes.github.fetch_github_issue import fetch_github_issue
# from taskmates.core.workflows.markdown_completion.markdown_completion import MarkdownCompletion
#
#
# @fulfills(outcome="github_issue_markdown_chat")
# async def get_github_issue_markdown_chat(issue_number, repo_name):
#     await set_github_access_token_env()
#
#     inputs = fetch_github_issue(issue_number, repo_name)
#     chat_content = compose_chat_from_github_issue(inputs)
#     return chat_content
#
#
# @fulfills(outcome="github_access_token_env")
# async def set_github_access_token_env():
#     env = os.environ
#
#     token_response = GithubAppInstallationToken(
#         env['GITHUB_APP_ID'],
#         env['GITHUB_APP_PRIVATE_KEY'],
#         env['GITHUB_APP_INSTALLATION_ID']
#     ).get()
#     env["GITHUB_ACCESS_TOKEN"] = token_response['token']
#
#
# class GithubIssue(Workflow):
#     async def steps(self,
#                     repo_name: str,
#                     issue_number: int,
#                     response_format: str = 'text',
#                     history_path: str = None
#                     ):
#         markdown_chat = await get_github_issue_markdown_chat(issue_number, repo_name)
#
#         # TODO: CHANGE CWD TO DEMO
#         return await MarkdownCompletion().fulfill(
#             markdown_chat=markdown_chat + "\n\nHey @demo_dev please have a look \n\n")
#
# # @pytest.mark.integration
# # async def test_github_issue(tmp_path):
# #     # TODO: use cli runner
# #     contexts = CliContextBuilder().build()
# #     await GithubIssue().fulfill(
# #         repo_name="taskmates/demo",
# #         issue_number=1,
# #         history_path=str(tmp_path / "history.md"))
