# Front Matter Options

Taskmates supports configuration through YAML front matter at the beginning of markdown chat files.

## Available Options

### Core Options

- **`model`**: Specifies the LLM model to use
    - Example: `model: gpt-4o` or `model: claude-3-haiku-20240307`

- **`max_steps`**: Maximum number of completion steps before stopping
    - Default: `10000`
    - Example: `max_steps: 50`

- **`jupyter_enabled`**: Enable/disable Jupyter code cell execution
    - Default: `true`
    - Example: `jupyter_enabled: false`

### Advanced Options

- **`system`**: System message to prepend to the chat
    - Example: `system: You are a helpful assistant`

- **`participants`**: Define custom participants and their configurations
    - Example:
      ```yaml
      participants:
        assistant:
          model: gpt-4o
          temperature: 0.7
      ```

- **`tools`**: Configure available tools and their permissions
    - Example:
      ```yaml
      tools:
        write_file:
          allow: "**/*.py"
          deny: "**/secrets/*"
      ```

- **`inputs`**: Define input variables for the chat
    - Example: `inputs: {name: "Alice", topic: "Python"}`

## Example

```yaml
---
model: claude-3-haiku-20240307
max_steps: 100
system: You are a Python expert
tools:
  write_file:
    allow: "src/**/*.py"
---
