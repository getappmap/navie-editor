def problem_statement_prompt(problem_statement: str) -> str:
    return f"""<problem-statement>
{problem_statement}
</problem-statement>
"""


def edit_prompt(file: str, plan: str, problem_statement: str) -> str:
    return f"""Edit file {file} according to the following plan, that addresses the problem statement.

<plan>
{plan}
</plan>

<error>
{problem_statement}
</error>
"""


def context_file_prompt(file: str) -> str:
    with open(file, "r", encoding="utf-8") as f:
        content_lines = f.readlines()
        # Print each line with the line number, 6 characters wide
        content = "".join(
            [f"{i+1:6}: {line}" for i, line in enumerate(content_lines)]
        )

    return f"""<file>
<path>{file}</path>
<contents><!CDATA[
{content}
]]></contents>
</file>
"""
