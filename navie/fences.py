def has_fences(content) -> bool:
    first_line, last_line = content.split("\n")[:2], content.split("\n")[-2:]
    return "```" in first_line and "```" in last_line


def extract_fenced_content(content: str) -> list[str]:
    content_lines = content.split("\n")
    extracted_content = []
    lines = []
    in_fence = False
    for line in content_lines:
        if line.startswith("```"):
            if not in_fence:
                in_fence = True
            else:
                extracted_content.append("\n".join(lines))
                lines = []
                in_fence = False
        elif in_fence:
            lines.append(line)

    if not len(extracted_content):
        return [content]

    return extracted_content
