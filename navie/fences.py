import os


def trim_single_backticks(content: str) -> str:
    if content.startswith("`") and content.endswith("`"):
        return content[1:-1]

    return content


def extract_fenced_content(content: str) -> list[str]:
    content_lines = content.splitlines()
    extracted_content = []
    lines = []
    in_fence = False
    for line in content_lines:
        if line.startswith("```"):
            if not in_fence:
                in_fence = True
            else:
                extracted_content.append(os.linesep.join(lines) + os.linesep)
                lines = []
                in_fence = False
        elif in_fence:
            lines.append(line)

    if not len(extracted_content):
        return [trim_single_backticks(content)]

    return extracted_content
