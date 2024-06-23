**user>** This is a message.

**assistant>** This is a response.

**user {"name": "john"}>** This is a message with attributes.

**assistant>** This is a response from the assistant.

**john>** This is another message from john.

**assistant>** This is a message with tool calls.

###### Steps

- Run Shell Command [1] `{"cmd":"echo hello"}`
- Run Shell Command [2] `{"cmd":"echo world"}`

###### Execution: Run Shell Command [1]

<pre class='output' style='display:none'>
hello

Exit Code: 0
</pre>

-[x] Done

###### Execution: Run Shell Command [2]

<pre class='output' style='display:none'>
world

Exit Code: 0
</pre>

-[x] Done

**user>** This is a message with code cells

```python .eval
print("hello")
```

```python .eval
print("world")
```

###### Cell Output: stdout [cell_0]

<pre>
hello
</pre>

###### Cell Output: stdout [cell_1]

<pre>
world
</pre>

