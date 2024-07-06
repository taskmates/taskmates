# Taskmates

Taskmates provides a powerful ecosystem of AI Agents that can interact with your everyday CLI tools and APIs.

The use of Taskmates requires an active subscription. Sign up for the Beta program [here](https://taskmates.me).

##### ⚠️ Disclaimer: Experimental and Potentially Dangerous

**Warning:** Taskmates is experimental and can potentially execute arbitrary commands on your system (e.g. via shell or python interpreter). Use at your own risk. We take no responsibility for any actions performed by Taskmates or any resulting damages.

## Plain Markdown: our backbone

Communicate with Taskmates using Markdown files, from any editor or the CLI.

## Quick Start

1. Create a Taskmate:

```bash
mkdir -p ${TASKMATES_HOME:-"/var/tmp/taskmates"}/my_taskmates
cat << EOF > ${TASKMATES_HOME:-"/var/tmp/taskmates"}/my_taskmates/git.md
---
tools:
  run_shell_command:
---

You a helpful AI agent specialized in the Git cli tool. Use the shell to interact with it. 
EOF
```

2. Interact with it by mentioning its username.

```bash
export ANTHROPIC_API_KEY="your_api_key"

taskmates complete "Hey @git, find the commit that deleted the file requirements.txt"
```

3. Or, start the websocket server (e.g. if you're a client other than the CLI)

```bash
taskmates server
```

## Installation

```bash
pipx install --force --python 3.11 git+https://github.com/taskmates/taskmates.git

# optionally, install pre-built Taskmates 
git clone https://@github.com/taskmates/taskmates-directory.git "${TASKMATES_HOME:-"/var/tmp/taskmates"}/taskmates"
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

## Support

Join our [Discord](https://discord.gg/XjdEqUZXUn) community for support and feedback.
