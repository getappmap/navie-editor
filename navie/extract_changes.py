import re
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional


class FileUpdate:
    def __init__(self, file: str, search: str, modified: str):
        self.file = file
        self.original = search
        self.modified = modified

    def __repr__(self):
        return f"FileUpdate(file={self.file}, original={self.original}, modified={self.modified})"

    def __eq__(self, other):
        return (
            isinstance(other, FileUpdate)
            and self.file == other.file
            and self.original == other.original
            and self.modified == other.modified
        )


def extract_changes(content: str) -> List[FileUpdate]:
    # Gemini tends to use ``` instead of closing CDATA properly.
    content = content.replace("```</", "]]></")

    # Search for <change> tags
    change_regex = re.compile(r"<change>([\s\S]*?)<\/change>", re.IGNORECASE)
    changes: List[FileUpdate] = []

    # Trim at most one leading and trailing blank lines
    def trim_content(content: str) -> str:
        return content.lstrip("\n").rstrip("\n")

    for match in change_regex.finditer(content):
        change = match.group(0)

        try:
            # Parse XML
            root = ET.fromstring(change)
            # Ensure the correct structure
            file = root.find("file")
            original = root.find("original")
            modified = root.find("modified")
            if (
                file is not None
                and original is not None
                and modified is not None
                and file.text is not None
                and original.text is not None
                and modified.text is not None
            ):
                update = FileUpdate(
                    file=trim_content(file.text),
                    search=trim_content(original.text),
                    modified=trim_content(modified.text),
                )
                changes.append(update)
            else:
                print(
                    f"[extract-changes] Change is missing a required field (file, original, or modified) : {change}"
                )
        except ET.ParseError:
            print(f"Failed to parse change: {change}")
            continue

    return changes
