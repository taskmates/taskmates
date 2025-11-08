import pytest


@pytest.fixture
def sample_project(tmp_path):
    """Create a sample Python project for testing."""
    # Create directory structure
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()

    # Create some Python files
    (src_dir / "parser.py").write_text("""
def parse_input(text: str) -> dict:
    '''Parse input text into a dictionary.'''
    lines = text.split('\\n')
    result = {}
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            result[key.strip()] = value.strip()
    return result


def format_output(data: dict) -> str:
    '''Format dictionary as text output.'''
    lines = []
    for key, value in data.items():
        lines.append(f"{key}: {value}")
    return '\\n'.join(lines)
""")

    (src_dir / "validator.py").write_text("""
def validate_email(email: str) -> bool:
    '''Validate email format.'''
    return '@' in email and '.' in email.split('@')[1]


def validate_phone(phone: str) -> bool:
    '''Validate phone number format.'''
    digits = ''.join(c for c in phone if c.isdigit())
    return len(digits) >= 10
""")

    (tests_dir / "test_parser.py").write_text("""
from src.parser import parse_input, format_output


def test_parse_input():
    text = "name: John\\nage: 30"
    result = parse_input(text)
    assert result == {"name": "John", "age": "30"}


def test_format_output():
    data = {"name": "John", "age": "30"}
    result = format_output(data)
    assert "name: John" in result
""")

    # Create a file that should be excluded
    pycache_dir = src_dir / "__pycache__"
    pycache_dir.mkdir()
    (pycache_dir / "parser.pyc").write_text("compiled bytecode")

    return tmp_path
