from dataclasses import dataclass
from typing import Dict, Any

import pyparsing as pp


@dataclass
class MetaTagNode:
    attributes: Dict[str, Any]
    source: str

    @classmethod
    def from_tokens(cls, tokens):
        source = tokens[0]
        
        # Parse attributes from the meta tag
        attributes = {}
        
        # Extract attribute pairs from the tag
        import re
        # Match attribute="value" or attribute='value' patterns
        attr_pattern = r'(\w+)\s*=\s*["\']([^"\']*)["\']'
        matches = re.findall(attr_pattern, source)
        
        raw_attributes = {}
        for attr_name, attr_value in matches:
            raw_attributes[attr_name] = attr_value
        
        # Transform HTML meta tag pattern into proper key-value pairs
        # If it has name="key" content="value", use key:value
        # Otherwise, use the raw attributes as-is
        if 'name' in raw_attributes and 'content' in raw_attributes:
            # Standard HTML meta tag pattern
            key = raw_attributes['name']
            value = raw_attributes['content']
            attributes[key] = value
        else:
            # Non-standard meta tag (e.g., charset="UTF-8")
            attributes = raw_attributes
            
        return cls(attributes=attributes, source=source)


def meta_tag_parser():
    # Match <meta ... /> or <meta ...> patterns
    meta_start = pp.LineStart() + pp.Literal("<meta")
    meta_attrs = pp.SkipTo(pp.Regex(r'/?>'), include=True)
    
    # Combine the entire meta tag line
    meta_line = (
        pp.Combine(
            meta_start + meta_attrs
        ) + pp.LineEnd()
    ).setName("meta_tag_line").set_parse_action(MetaTagNode.from_tokens)
    
    return meta_line


def test_basic_meta_tag():
    input = '<meta name="foo" content="bar" />\n'
    result = meta_tag_parser().parseString(input)[0]
    assert result.source == '<meta name="foo" content="bar" />'
    assert result.attributes == {'foo': 'bar'}  # Transformed from name/content pattern


def test_meta_tag_single_quotes():
    input = "<meta name='description' content='A test description' />\n"
    result = meta_tag_parser().parseString(input)[0]
    assert result.source == "<meta name='description' content='A test description' />"
    assert result.attributes == {'description': 'A test description'}  # Transformed


def test_meta_tag_without_slash():
    input = '<meta charset="UTF-8">\n'
    result = meta_tag_parser().parseString(input)[0]
    assert result.source == '<meta charset="UTF-8">'
    assert result.attributes == {'charset': 'UTF-8'}  # No transformation needed


def test_meta_tag_multiple_attributes():
    input = '<meta name="viewport" content="width=device-width, initial-scale=1.0" />\n'
    result = meta_tag_parser().parseString(input)[0]
    assert result.source == '<meta name="viewport" content="width=device-width, initial-scale=1.0" />'
    assert result.attributes == {'viewport': 'width=device-width, initial-scale=1.0'}  # Transformed


def test_meta_tag_with_spaces():
    input = '<meta   name="author"   content="John Doe"   />\n'
    result = meta_tag_parser().parseString(input)[0]
    assert result.source == '<meta   name="author"   content="John Doe"   />'
    assert result.attributes == {'author': 'John Doe'}  # Transformed


def test_meta_tag_empty_content():
    input = '<meta name="empty" content="" />\n'
    result = meta_tag_parser().parseString(input)[0]
    assert result.source == '<meta name="empty" content="" />'
    assert result.attributes == {'empty': ''}  # Transformed
