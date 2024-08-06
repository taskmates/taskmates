# Taskmates

Taskmates provides a powerful ecosystem of AI Agents that can interact with your everyday CLI tools and APIs.

The use of Taskmates requires an active subscription. Sign up for the Beta program [here](https://taskmates.me).

⚠️ **Warning:
** Taskmates is experimental and can potentially execute arbitrary commands on your system (e.g. via shell or python interpreter). Use at your own risk. We take no responsibility for any actions performed by Taskmates or any resulting damages.

## Who is this for?

Taskmates is currently targeted at experienced developers or companies.

## What can it do?

### Some of the things it can do well

- Complex tasks where an automated feedback loop is feasible:
    - Read your code, edit it, run unit tests, read the output, fix it, repeat.
    - Run CLI tools, read the output, make adjusments, repeat.
    - Write a small POC (e.g. of a library), execute it, read the output, make adjustments, repeat.
- Use CLI tools. For example, create a taskmate specialized in `git`, `docker`, `aws`, etc. When using less popular tools, print the help message and add it to their instruction.
- Use APIs. For example, create a taskmate specialized in the GitHub API, Jira API, etc. Simply instruct the taskmate to use the REST API via CURL. If the API is unknown, add its documentation to the instruction.
- Interpret images. Give it a screenshot or a diagram and ask it to describe what it sees, or write/fix code based on it.

### Some of the things it can't do so well (yet)

- Write large a project or large amounts of code from scratch.
    - Try to do it iteratively, incrementally. Organize your code in well-encapsulated components.
- Edit code that has a lot of dependencies or that is too large (e.g. thousands of lines).
    - Performance of all current AI models seem to degrade as the content gets larger.
- Code with complex execution flows (e.g. multiple threads, async code, recursion).
    - It might help to ask them to print debug statements and run it, so they can follow the execution flow.

Please note that they can and are getting better (at a fast speed) via:

- Optimized Taskmates Prompts (soon to come)
- Optimized workflows (soon to come)
- New and better AI models (e.g. from OpenAI and Anthropic)

## Installation

```bash
# install pipx
brew install pipx
pipx ensurepath
sudo pipx ensurepath --global # optional to allow pipx actions with --global argument

# install/update taskmates
pipx install --force --python 3.11 git+https://github.com/taskmates/taskmates.git

# install pre-built Taskmates 
git clone https://@github.com/taskmates/taskmates-directory.git "${TASKMATES_HOME:-"$HOME/.taskmates"}/taskmates"

# test installation
export TASKMATES_API_KEY=<your_api_key>
taskmates complete "Hey @taskmates what can you do?"
```

## Quick Start

1. Create a Taskmate:

```bash
mkdir -p ${TASKMATES_HOME:-"$HOME/.taskmates"}/my_taskmates
cat << EOF > ${TASKMATES_HOME:-"$HOME/.taskmates"}/my_taskmates/git.md
---
tools:
  run_shell_command:
---

You a helpful AI agent specialized in the Git cli tool. Use the shell to interact with it. 
EOF
```

2. Interact with it by mentioning its username.

```bash
taskmates complete "Hey @git, find the commit that deleted the file requirements.txt"
```

3. Or, start the websocket server (e.g. if you're a client other than the CLI)

```bash
taskmates server
```

## The Chat Markdown format

Each prompt **[username]>** indicates the start of a message (the initial user prompt is implicit/optional):

    Hello
    
    **assistant>** How can I help you?

    **user>** 

Mention a taskmate to bring them to the chat. The Steps section indicate tools calls, e.g. Run Shell Command:

    **user>** Hey @shell what's the current directory?
    
    **shell>** Certainly!
    
    ###### Steps
    
    - Run Shell Command [1] `{"cmd": "pwd"}`
    
    ###### Execution: Run Shell Command [1]
    
    <pre class='output' style='display:none'>
    /tmp
    </pre>
    
    -[x] Done
    
    **shell>** The current directory is: /tmp

Code cells marked .eval are executed:

    **user>** Hey @jupyter, what's the current directory? // Mention another taskmate

    **jupyter>** Certainly!

    ```python .eval
    !pwd
    ```

    ###### Cell Output: stdout [cell_0]

    <pre>
    /tmp
    </pre>

    **jupyter>** The current directory is: /tmp

    **user>**

Use transclusions for more advanced use cases:

    **user>** Please fix the alignment of the blue button.
    
    ![[/path/to/screenshot.png]]

    My css:

    ![[/path/to/code/main.css]]

    My html:

    ![[/path/to/code/index.html]]

## Security

Taskmates can execute arbitrary commands on your system. Consider running it in a sandboxed environment (e.g. Docker) or on a dedicated machine.

## License

Taskmates will require a commercial license to use. It will be free for some cases (e.g. individual use, open-source projects, educational purposes), and parts of it likely open source. We're still figuring out the details.

## Support

Join our [Discord](https://discord.gg/XjdEqUZXUn) community for support and feedback.

## Join us

We're looking for co-founders and individual contributors. Reach out to us via <a href="https://www.linkedin.com/company/taskmatesme">LinkedIn</a>
