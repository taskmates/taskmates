import re
from pathlib import Path
from urllib.parse import unquote

FILE_TRANSCLUSION_PATTERN = re.compile(r"^!\[\[(.+?)(#(.+?))?\]\]$|^!\[(.*?)\]\((.+?)\)$", re.MULTILINE)


def extract_transclusion_links(content, base_path=None):
    matches = re.finditer(FILE_TRANSCLUSION_PATTERN, content)
    links = []
    for match in matches:
        if match.group(1) or match.group(5):
            target_glob = unquote(match.group(1) or match.group(5))
            if base_path:
                target_glob = str((Path(base_path) / target_glob).resolve())
            links.append(target_glob)
    return links


def test_extract_transclusion_links_with_square_brackets():
    content = "Hello\n![[path/to/image.jpg]]"
    links = extract_transclusion_links(content)
    assert links == ["path/to/image.jpg"]


def test_extract_transclusion_links_with_parentheses():
    content = "Hello\n![alt text](path/to/image.png)"
    links = extract_transclusion_links(content)
    assert links == ["path/to/image.png"]


def test_extract_transclusion_links_with_multiple_links():
    content = "Hello\n![[path/to/image1.jpg]]\n![alt text](path/to/image2.png)"
    links = extract_transclusion_links(content)
    assert links == ["path/to/image1.jpg", "path/to/image2.png"]


def test_extract_transclusion_links_with_no_links():
    content = "Hello, no image links here"
    links = extract_transclusion_links(content)
    assert links == []


def test_extract_transclusion_links_with_encoded_url():
    content = "Hello\n![[path/to/image%20with%20spaces.jpg]]"
    links = extract_transclusion_links(content)
    assert links == ["path/to/image with spaces.jpg"]
