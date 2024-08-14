"""
This module provides the Troubleshoot class, which is used to address and solve error messages
by generating and applying code changes based on a given error message and context.

Classes:
    Troubleshoot: Handles the troubleshooting process by generating and applying code changes.

Usage example:
    troubleshoot = Troubleshoot(work_dir, error_message)
    troubleshoot.solve()
"""

import argparse
import os
import hashlib

from navie.editor import Editor
from navie.format_instructions import xml_format_instructions
from navie.extract_changes import extract_changes


class Troubleshoot:
    """
    Class Troubleshoot

    This class is used for troubleshooting issues. It contains methods and functionalities aimed at identifying, analyzing,
    and resolving various problems that might occur within the system.

    Attributes:
    - work_dir (str): The working directory where troubleshooting files are stored.
    - error_message (str): The error message to be addressed.
    - files (list): A list to store file paths related to the troubleshooting process.

    Methods:
    - solve: Executes the troubleshooting plan to resolve the error message.
    """

    def __init__(self, work_dir, error_message: str):
        """
        Initialize the Troubleshoot class.

        Args:
            work_dir (str): The working directory where troubleshooting files are stored.
            error_message (str): The error message to be addressed.

        Attributes:
            work_dir (str): The working directory where troubleshooting files are stored.
            error_message (str): The error message to be addressed.
            files (list): A list to store file paths related to the troubleshooting process.
        """
        self.work_dir = work_dir
        self.error_message = error_message
        self.directions = None
        self.files = []

        self._plan = None
        self._files_to_edit = []

    def plan(self):
        plan_dir = os.path.join(self.work_dir, "plan")
        editor = Editor(plan_dir)
        messages = []

        if self.directions:
            messages.append(self.directions)

        messages.append(
            f"""<error>
{self.error_message}
</error>
"""
        )

        self._apply_files(messages)

        self._plan = editor.plan("\n\n".join(messages))
        self._files_to_edit = editor.list_files(self._plan)
        print(f"Files to edit: {self._files_to_edit}")
        return self._plan

    def apply(self):
        for file in self._files_to_edit:
            # Compute sha1 of the file
            with open(file, "rb") as f:
                file_sha1 = hashlib.sha1(f.read()).hexdigest()
            edit_dir = os.path.join(self.work_dir, "edit", file_sha1)

            messages = []
            messages.append(
                f"""Edit file {file} according to the following plan, that fixes the described error.

<plan>
{self._plan}
</plan>

<error>
{self.error_message}
</error>
"""
            )

            self._apply_files(messages)

            editor = Editor(edit_dir)
            code = editor.generate(
                "\n".join(messages), prompt=xml_format_instructions()
            )
            changes = extract_changes(code)
            for change in changes:
                editor.apply(change.file, change.modified, search=change.original)

    def _apply_files(self, messages):
        if not self.files:
            return

        for file in self.files:
            with open(file, "r", encoding="utf-8") as f:
                content_lines = f.readlines()
                # Print each line with the line number, 6 characters wide
                content = "\n".join(
                    [f"{i+1:6}: {line}" for i, line in enumerate(content_lines)]
                )

            context_file_str = f"""<file>
<path>{file}</path>
<contents><!CDATA[
{content}
]]></contents>
</file>
"""
            messages.append(context_file_str)

    def __repr__(self):
        return f"Troubleshoot(error_message={self.error_message})"


def main():
    error_message = input()
    error_message_sha1 = hashlib.sha1(error_message.encode()).hexdigest()

    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--workdir", help="Work directory")
    args = parser.parse_args()
    work_dir = args.workdir
    if not work_dir:
        work_dir = os.path.join(
            os.getcwd(), ".navie", "troubleshoot", error_message_sha1
        )
        os.makedirs(work_dir, exist_ok=True)

    troubleshoot = Troubleshoot(work_dir, error_message)
    while True:
        print("Planning...")
        plan = troubleshoot.plan()
        print(f"\033[92mPlan:\033[0m\n\n{plan}")

        # Prompt the user for adjustments they may want to make. Allow multi-line input terminated by Ctrl-D.
        adjustments = []
        print("Enter any adjustments you want to make (end with Ctrl-D):")
        try:
            while True:
                line = input()
                adjustments.append(line)
        except EOFError:
            pass

        adjustments = "\n".join(adjustments)
        if not adjustments:
            break

        troubleshoot.directions = adjustments

    troubleshoot.apply()


if __name__ == "__main__":
    main()
