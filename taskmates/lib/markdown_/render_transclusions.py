import glob
import re
from pathlib import Path
from typing import Union
from urllib.parse import unquote

import pytest
from typeguard import typechecked

from taskmates.formats.markdown.processing.extract_transclusion_links import extract_transclusion_links
from taskmates.formats.markdown.processing.filter_comments import filter_comments
from taskmates.lib.markdown_.first_sections_with_heading import first_sections_with_heading
from taskmates.lib.markdown_.language_mappings import language_mappings
from taskmates.lib.markdown_.transclusion_pattern import match_transclusion
from taskmates.lib.path_.is_binary_file import is_binary_file
from taskmates.lib.pdf_.read_pdf import read_pdf
from taskmates.lib.root_path.root_path import root_path


@typechecked
def render_transclusions(text: str,
                         source_file: Path,
                         processed_files=None,
                         is_embedding=False):
    transclusions_base_dir = source_file.parent
    text = filter_comments(text)
    if processed_files is None:
        processed_files = set()

    output = []
    lines = text.split('\n')
    for i, line in enumerate(lines):
        match = match_transclusion(line)
        if not match:
            output.append(line)
            continue

        transclusion_token = Transclusion(match, transclusions_base_dir)
        transclusion_path = transclusion_token.target_glob
        if transclusion_path in processed_files:
            raise RecursionError(f"Transclusion cycle detected: {transclusion_path}")

        embedding = line.startswith('![')
        processed_files.add(transclusion_path)

        transclusion_output = process_transclusion(transclusion_token,
                                                   source_file=source_file,
                                                   is_embedding=embedding)

        is_content = i < len(lines) - 1 and lines[i + 1].strip()
        if is_content:
            transclusion_output[-1] = transclusion_output[-1].rstrip('\n') + '\n'
        else:
            transclusion_output[-1] = transclusion_output[-1].rstrip('\n')
        output.extend(transclusion_output)
    final_output = '\n'.join(output) if not is_embedding else ''.join(output)

    transclusion_links = extract_transclusion_links(final_output)
    non_binary_links = [link for link in transclusion_links if not is_binary_file(link)]

    if non_binary_links:
        raise ValueError(f"Transclusion links {transclusion_links} not found")
    return final_output


class Transclusion:
    def __init__(self, matched_link, transclusions_base_dir: Union[Path, str]):
        if "#" in matched_link:
            link, separator, section = unquote(matched_link).partition('#')
            section = separator + section
        else:
            link = unquote(matched_link)
            section = None
        self.section = section
        self.target_glob = link
        self.transclusions_base_dir: Union[Path, str] = transclusions_base_dir


def escape_glob_pattern(pattern):
    # Escape special characters for glob patterns
    special_chars = ['*', '?', '[', ']']
    for char in special_chars:
        pattern = pattern.replace(char, f'[{char}]')
    return pattern


@typechecked
def process_transclusion(token: Transclusion,
                         source_file: Path,
                         is_embedding=False):
    transclusions_base_dir = source_file.parent
    fragments = []
    target_glob = token.target_glob
    # print(f"Processing transclusion for: {target_glob}")  # Debug print
    if "*" in target_glob:
        filenames = list(sorted(glob.glob(target_glob, root_dir=transclusions_base_dir)))
    else:
        filenames = [target_glob]

    if len(filenames) == 0:
        raise ValueError(f"No files found matching glob pattern: {token.target_glob}")
    for filename in filenames:
        resolved_path = (Path(transclusions_base_dir) / filename).resolve()
        try:
            if filename.lower().endswith('.pdf'):
                content = read_pdf(resolved_path)
            else:
                if not resolved_path.exists():
                    raise ValueError(f"Transclusion not found: {resolved_path}. Source file: {source_file}")
                with open(resolved_path, 'r') as f:
                    content = f.read()
        except UnicodeDecodeError:
            fragments.append(f"![[{filename}]]")
            continue
        if token.section:
            heading = re.sub(r'^(#+)', r'\1 ', token.section)
            sections = first_sections_with_heading(content, heading)
            if len(sections) == 0:
                raise ValueError(f"Section not found: {token.section}")
            section = sections[-1]
            full_source: str = section["full_source"]
            without_heading = "\n".join(full_source.splitlines()[1:])
            fragments.append(without_heading)
            continue
        extension = Path(filename).suffix.lstrip('.')
        if extension == Path(filename).suffix:
            language = Path(filename).suffix
        elif extension not in language_mappings:
            language = extension
        else:
            language = language_mappings[extension]["language_hint"]

        if is_embedding:
            fragments.append(render_transclusions(content,
                                                  source_file=resolved_path,
                                                  processed_files={filename}))
        else:
            if transclusions_base_dir and not Path(filename).is_absolute():
                path = (Path(transclusions_base_dir) / filename).relative_to(transclusions_base_dir)
            else:
                path = Path(filename)
            fragments.append(format_transclusion(path, language, content))
    return fragments


def transclude(path):
    extension = path.suffix.lstrip('.')
    if extension not in language_mappings:
        language = extension
    else:
        language = language_mappings[extension]["language_hint"]
    return format_transclusion(path, language, path.read_text())


def format_transclusion(path, language, content):
    language_hint = language_mappings.get(language, {}).get('language_hint', '')

    return f"The following are the contents of the file {path}:\n\n" \
           f"\"\"\"\"\n{content}\n\"\"\"\"\n"


def test_transclusion_renderer(tmp_path):
    d = tmp_path / "sub"
    d.mkdir()
    p = d / "foo.py"
    p.write_text("print('Hello, world!')\n")
    doc = '#[[{}]]\n'.format(str(p))
    rendered = render_transclusions(doc, source_file=tmp_path / "main.md")
    expected = transclude(p)
    assert rendered == expected


def test_transclusion_renderer_no_match(tmp_path):
    doc = '[[*.py]]'  # missing '#'
    rendered = render_transclusions(doc, source_file=tmp_path / "main.md")
    assert rendered == '[[*.py]]'


def test_transclusion_renderer_multiple_files(tmp_path):
    d = tmp_path / "sub"
    d.mkdir()
    p1 = d / "0-foo.py"
    p1.write_text("print('Hello, world!')\n")
    p2 = d / "1-bar.py"
    p2.write_text("print('Goodbye, world!')\n")
    doc = '#[[{}/*.py]]\n'.format(str(d))
    rendered = render_transclusions(doc, source_file=tmp_path / "main.md")
    expected = map(transclude, [p1, p2])
    assert rendered == "\n".join(expected)


def test_transclusion_renderer_target_glob(tmp_path):
    d = tmp_path / "sub"
    d.mkdir()
    p1 = d / "0-foo.py"
    p1.write_text("print('Hello, world!')\n")
    p2 = d / "1-bar.py"
    p2.write_text("print('Goodbye, world!')\n")
    d2 = tmp_path / "sub2"
    d2.mkdir()
    p3 = d2 / "2-baz.py"
    p3.write_text("print('Hello again, world!')\n")
    d4 = tmp_path / "sub4"
    d4.mkdir()
    doc = '#[[{}/**/*.py]]\n'.format(str(tmp_path))
    rendered = render_transclusions(doc, source_file=tmp_path / "main.md")
    expected = map(transclude, [p1, p2, p3])
    assert rendered == "\n".join(expected)


def test_transclusion_renderer_skips_binary_files(tmp_path):
    # Create a binary file (e.g., a simple PNG image)
    binary_file_path = tmp_path / "image.png"
    binary_file_path.write_bytes(
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDAT\x08\xd7c\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa7^\xea\x83\x00\x00\x00\x00IEND\xaeB`\x82')

    # Render the document with both text and binary file transclusions
    doc = f'Hello\n\n![[{tmp_path}/image.png]]'  # Glob pattern should match both files
    rendered = render_transclusions(doc, source_file=tmp_path / "main.md")

    assert rendered == doc


def test_embedding_transclusion(tmp_path):
    sub_dir = tmp_path / "sub"
    sub_dir.mkdir()
    foo_path = sub_dir / "foo.md"
    foo_path.write_text("![[bar.md]]\n")
    bar_path = sub_dir / "bar.md"
    bar_path.write_text("Hello, world!\n")
    doc = '![[{}/foo.md]]\n'.format(str(sub_dir))
    rendered = render_transclusions(doc, source_file=sub_dir / "main.md")
    expected = "Hello, world!\n"
    assert rendered == expected


def test_embedding_transclusion_with_cycle(tmp_path):
    sub_dir = tmp_path / "sub"
    sub_dir.mkdir()
    foo_path = sub_dir / "foo.md"
    foo_path.write_text("![[bar.md]]\n")
    bar_path = sub_dir / "bar.md"
    bar_path.write_text("![[foo.md]]\nHello, world!\n")
    doc = '![[{}/*.md]]'.format(str(sub_dir))

    with pytest.raises(RecursionError):
        render_transclusions(doc, source_file=sub_dir / "main.md")


def test_transclusion_token_markdown_format(tmp_path):
    match = match_transclusion('#[My Link](..%2F..%2Flink%2Fto%2Ffile)')
    token = Transclusion(match, tmp_path)
    assert token.target_glob == '../../link/to/file'


def test_transclusion_token_markdown_format_url_encoded(tmp_path):
    match = match_transclusion('#[My Link](..%2F..%2Flink%2Fto%2Ffile)')
    token = Transclusion(match, tmp_path)
    assert token.target_glob == '../../link/to/file'


def test_transclusion_token_markdown_format_multiple_url_encoded_characters(tmp_path):
    match = match_transclusion('#[My Link](..%2F..%2Flink%2Fto%2Ffile%20with%20spaces)')
    token = Transclusion(match, tmp_path)
    assert token.target_glob == '../../link/to/file with spaces'


def test_transclusion_token_markdown_format_special_characters(tmp_path):
    match = match_transclusion('#[My Link](..%2F..%2Flink%2Fto%2Ffile%23with%23hashes)')
    token = Transclusion(match, tmp_path)
    assert token.target_glob == '../../link/to/file#with#hashes'


def test_transclusion_token_wikilink_format(tmp_path):
    match = match_transclusion('![[bar.md]]')
    token = Transclusion(match, tmp_path)
    assert token.target_glob == 'bar.md'


def test_transclusion_token_wikilink_format_with_section(tmp_path):
    match = match_transclusion('![[bar.md#section1]]')
    token = Transclusion(match, tmp_path)
    assert token.target_glob == 'bar.md'
    assert token.section == '#section1'


def test_process_transclusion_relative_path_resolution(tmp_path):
    d = tmp_path / "sub"
    d.mkdir()
    p = d / "foo.md"
    p.write_text("Content of foo.md")
    token = Transclusion('foo.md', str(d))
    fragments = process_transclusion(token,
                                     source_file=d / "main.md",
                                     is_embedding=True)
    assert len(fragments) == 1
    assert fragments[0] == "Content of foo.md"


def test_cycle_detection(tmp_path):
    directory = tmp_path / "sub"
    directory.mkdir()
    path_1 = directory / "foo.md"
    path_1.write_text("![[bar.md]]\n")
    path_2 = directory / "bar.md"
    path_2.write_text("![[foo.md]]\n")
    token1 = Transclusion('foo.md', str(directory))
    token2 = Transclusion('bar.md', str(directory))
    with pytest.raises(RecursionError):
        process_transclusion(token1, source_file=directory / "main.md",
                             is_embedding=True)
        process_transclusion(token2, source_file=directory / "main.md",
                             is_embedding=True)


def test_transclusion_renderer_section(tmp_path):
    directory = tmp_path / "sub"
    directory.mkdir()
    path = directory / "bar.md"
    path.write_text("# section1\nHello, world!\n# section2\nGoodbye, world!")
    doc = f"![[{path}#section1]]"
    rendered = render_transclusions(doc, source_file=tmp_path / "main.md")
    assert rendered == 'Hello, world!'


def test_transclusion_renderer_section_fragment(tmp_path):
    directory = tmp_path / "sub"
    directory.mkdir()
    path = directory / "file.md"
    path.write_text("# My Heading\nContent under my heading\n# Another Heading\nOther content")
    doc = f"![[{path}#My Heading]]"
    rendered = render_transclusions(doc, source_file=tmp_path / "main.md")
    expected = "Content under my heading\n"
    assert rendered.strip() == expected.strip()


def test_pdf_transclusion(tmp_path):
    pdf_path = root_path() / "tests/sample.pdf"

    doc = f'![[{pdf_path}]]'
    rendered = render_transclusions(doc, source_file=tmp_path / "main.md")
    expected = "The sky is blue\n"
    assert rendered.strip() == expected.strip()
