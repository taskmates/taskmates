import re

import inflection


def to_snake_case(text):
    return inflection.underscore(re.sub(" ", "_", text))


def test_to_snake_case_with_spaces():
    assert to_snake_case("Hello World") == "hello_world"


def test_to_snake_case_with_camel_case():
    assert to_snake_case("helloWorld") == "hello_world"


def test_to_snake_case_with_pascal_case():
    assert to_snake_case("HelloWorld") == "hello_world"
