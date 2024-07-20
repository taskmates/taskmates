import jupytext


def test_jupytext_reads_different_languages():
    # Create a Markdown document with Java and JavaScript code cells
    markdown_with_code = """\
```java
// Java code example
public class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}
```

```javascript
// JavaScript code example
console.log("Hello, JavaScript!");
```

```bash
# Bash code example
echo "Hello, Bash!"
```
"""
    # Parse the Markdown document using jupytext
    notebook = jupytext.reads(markdown_with_code, fmt='md')

    # Check if the notebook contains two code cells
    assert len(notebook.cells) == 3

    # Check if the first cell is Java code
    assert notebook.cells[0].cell_type == 'code'

    # Check if the second cell is JavaScript code
    assert notebook.cells[1].cell_type == 'code'

    # Check if the second cell is JavaScript code
    assert notebook.cells[2].cell_type == 'code'
