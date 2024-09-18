from typing import List
from navie.extract_changes import (
    extract_changes,
    FileUpdate,
)


def test_extract_changes_valid():
    content = """
    <change>
        <file>example.py</file>
        <original>print("Hello, World!")</original>
        <modified>print("Hello, Universe!")</modified>
    </change>
    """
    expected = [
        FileUpdate(
            file="example.py",
            search='print("Hello, World!")',
            modified='print("Hello, Universe!")',
        )
    ]
    result = extract_changes(content)
    assert result == expected


def test_extract_changes_missing_fields_2():
    content = """
    <change>
        <file>example.py</file>
        <original>print("Hello, World!")</original>
    </change>
    """
    result = extract_changes(content)
    assert result == []  # Should return an empty list due to missing 'modified' field


def test_extract_changes_missing_element_text():
    content = """
    <change>
        <file>example.py</file>
        <original>print("Hello, World!")</original>
        <modified />
    </change>
    """
    result = extract_changes(content)
    assert (
        result == []
    )  # Should return an empty list due to missing 'modified.text' field


def test_extract_changes_invalid_xml_2():
    content = """
    <change>
        <file>example.py</file>
        <original>print("Hello, World!")</original>
        <modified>print("Hello, Universe!")
    </change>
    """
    result = extract_changes(content)
    assert result == []  # Should return an empty list due to XML parsing error


def test_extract_changes_multiple_changes_2():
    content = """
    <change>
        <file>example1.py</file>
        <original>print("Hello, World!")</original>
        <modified>print("Hello, Universe!")</modified>
    </change>
    <change>
        <file>example2.py</file>
        <original>print("Goodbye, World!")</original>
        <modified>print("Goodbye, Universe!")</modified>
    </change>
    """
    expected = [
        FileUpdate(
            file="example1.py",
            search='print("Hello, World!")',
            modified='print("Hello, Universe!")',
        ),
        FileUpdate(
            file="example2.py",
            search='print("Goodbye, World!")',
            modified='print("Goodbye, Universe!")',
        ),
    ]
    result = extract_changes(content)
    assert result == expected


def test_extract_changes_valid_input():
    content = """
    <change>
        <file>/path/to/file.py</file>
        <original>print("Hello, World!")</original>
        <modified>print("Hello, Python!")</modified>
    </change>
    """
    expected = [
        FileUpdate(
            file="/path/to/file.py",
            search='print("Hello, World!")',
            modified='print("Hello, Python!")',
        )
    ]
    result = extract_changes(content)
    assert result == expected


def test_extract_changes_missing_fields():
    content = """
    <change>
        <file>/path/to/file.py</file>
        <original>print("Hello, World!")</original>
    </change>
    """
    result = extract_changes(content)
    assert result == []


def test_extract_changes_invalid_xml():
    content = """
    <change>
        <file>/path/to/file.py</file>
        <original>print("Hello, World!")</original>
        <modified>print("Hello, Python!")
    </change>
    """
    result = extract_changes(content)
    assert result == []


def test_extract_changes_multiple_changes():
    content = """
    <change>
        <file>/path/to/file1.py</file>
        <original>print("Hello, World!")</original>
        <modified>print("Hello, Python!")</modified>
    </change>
    <change>
        <file>/path/to/file2.py</file>
        <original>print("Goodbye, World!")</original>
        <modified>print("Goodbye, Python!")</modified>
    </change>
    """
    expected = [
        FileUpdate(
            file="/path/to/file1.py",
            search='print("Hello, World!")',
            modified='print("Hello, Python!")',
        ),
        FileUpdate(
            file="/path/to/file2.py",
            search='print("Goodbye, World!")',
            modified='print("Goodbye, Python!")',
        ),
    ]
    result = extract_changes(content)
    assert result == expected


def test_extract_changes_nonascii_characters():
    content = """
    <change>
        <file>example.py</file>
        <original>print("Hello, World!")</original>
        <modified>print("Hello, Universe! 😊")</modified>
    </change>
    """
    expected = [
        FileUpdate(
            file="example.py",
            search='print("Hello, World!")',
            modified='print("Hello, Universe! 😊")',
        )
    ]
    result = extract_changes(content)
    assert result == expected


if __name__ == "__main__":
    pytest.main()
