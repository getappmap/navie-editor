"""
This module provides the Edit class, which is used to address and solve error messages
by generating and applying code changes based on a given error message and context.

Classes:
    Edit: Handles the edit process by generating and applying code changes.

Usage example:
    edit = Edit(work_dir, problem_statement)
    edit.solve()
"""

import argparse
import difflib
import hashlib
import os
import readline
import sys

from navie.editor import Editor
from navie.extract_changes import extract_changes
from navie.format_instructions import xml_format_instructions
from navie.mode.quit_exception import QuitException

from .interactions import Interactions
from .prompt import context_file_prompt, edit_prompt, problem_statement_prompt
from .user_interface import UserInterface


class Edit:
    """
    Class Edit

    This class is used to edit code. It contains methods and functionalities aimed at identifying, analyzing,
    and resolving various problems that might occur within the system.

    Attributes:
    - work_dir (str): The working directory where working files are stored.
    - problem_statement (str): The problem to be addressed.

    Methods:
    - solve: Executes the plan to implement the problem statement.
    """

    def __init__(self, work_dir, problem_statement: str):
        self.work_dir = work_dir
        self.problem_statement = problem_statement
        self.files = []
        self.interactive = True
        self._plan = None
        self.files_to_edit = []

    def plan(self):
        plan_dir = os.path.join(self.work_dir, "plan")
        editor = Editor(plan_dir)
        messages = []

        messages.append(problem_statement_prompt(self.problem_statement))

        Edit.add_file_contents_to_messages(self.files, messages)

        messages.append(
            "Do not emit code or code snippets. Just describe the changes to each file."
        )

        self._plan = editor.plan("\n\n".join(messages))
        self.files_to_edit = editor.list_files(self._plan)

        return self._plan

    def apply(self, confirm_diff):
        for file in self.files_to_edit:
            # Compute sha1 of the file
            with open(file, "rb") as f:
                file_sha1 = hashlib.sha1(f.read()).hexdigest()
            edit_dir = os.path.join(self.work_dir, "edit", file_sha1)

            messages = []
            messages.append(edit_prompt(file, self._plan, self.problem_statement))

            Edit.add_file_contents_to_messages(self.files, messages)

            editor = Editor(edit_dir)
            code = editor.generate(
                "\n".join(messages), prompt=xml_format_instructions()
            )
            changes = extract_changes(code)

            file_sha1 = hashlib.sha1(file.encode()).hexdigest()
            temp_file_base = os.path.join(
                edit_dir,
                "_".join([file_sha1, ".".join([os.path.basename(file), "base"])]),
            )
            temp_file = os.path.join(
                edit_dir, "_".join([file_sha1, os.path.basename(file)])
            )
            with open(file, "r", encoding="utf-8") as f:
                base_lines = f.readlines()
                contents = "".join(base_lines)
                with open(temp_file_base, "w", encoding="utf-8") as f_temp:
                    f_temp.write(contents)
                with open(temp_file, "w", encoding="utf-8") as f_temp:
                    f_temp.write(contents)

            for change in changes:
                editor.apply(temp_file, change.modified, search=change.original)

            # Diff temp_file_base and temp_file using Python diff library
            with open(temp_file, "r", encoding="utf-8") as f_temp:
                changed_lines = f_temp.readlines()

            diff = difflib.unified_diff(
                base_lines, changed_lines, fromfile=file, tofile=file
            )
            if not diff:
                print(f"No changes for file {file}")
                continue

            diff_output = "".join(diff)

            if confirm_diff(file, diff_output):
                with open(file, "w", encoding="utf-8") as f:
                    f.write("".join(changed_lines))

    @staticmethod
    def add_file_contents_to_messages(files, messages):
        if not files:
            return

        for file in files:
            messages.append(context_file_prompt(file))

    def __repr__(self):
        return f"Edit(problem_statement={self.problem_statement})"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--directory", help="Program working directory")
    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="Run in non-interactive mode",
    )
    parser.add_argument("-i", "--issue", help="Issue description")
    parser.add_argument(
        "-f",
        "--file",
        action="append",
        dest="files",
    )
    args = parser.parse_args()

    if args.directory:
        os.chdir(args.directory)

    interactive = True if not args.no_interactive else False

    user_interface = UserInterface()
    if interactive:
        interactions = Interactions(user_interface)
    else:
        interactions = None

    problem_statement = args.issue
    if not problem_statement:
        if not interactive:
            print("Error: Issue description is required in non-interactive mode")
            sys.exit(1)

        problem_statement = interactions.collect_problem_statement()

    if not problem_statement.strip():
        print("Problem statement is empty. Exiting.")
        sys.exit(1)

    issue_sha1 = hashlib.sha1(problem_statement.encode()).hexdigest()

    work_dir = os.path.join(".navie", "edit", issue_sha1)
    os.makedirs(work_dir, exist_ok=True)

    print("Solving in directory {}".format(UserInterface.colorize(work_dir, "white")))

    edit = Edit(work_dir, problem_statement)
    if not interactive:
        edit.interactive = False
    if args.files:
        edit.files = args.files

    # Configure readline to use history file
    histfile = os.path.join(work_dir, ".edit_history")
    try:
        readline.read_history_file(histfile)
    except FileNotFoundError:
        pass

    try:
        replan_required = True
        while replan_required:
            replan_required = False
            user_interface.display_message("Planning...")
            plan = edit.plan()

            user_interface.display_message("")
            user_interface.display_message(plan)
            user_interface.display_message("")
            user_interface.display_message(f"Files to edit:")
            for file in edit.files_to_edit:
                user_interface.display_message(f"  {file}", color="white")

            if interactive:
                if interactions.prompt_for_edit():
                    updated_problem_statement = (
                        interactions.prompt_user_for_adjustments(edit.problem_statement)
                    )
                    if updated_problem_statement != edit.problem_statement:
                        edit.problem_statement = updated_problem_statement
                        replan_required = True

                    updated_files = interactions.prompt_user_for_adjustments(
                        "\n".join(edit.files_to_edit)
                    )
                    if updated_files != "\n".join(edit.files_to_edit):
                        edit.files_to_edit = [
                            file.strip()
                            for file in updated_files.split("\n")
                            if file.strip()
                        ]

        user_interface.display_message("Generating code...")

        if not interactive:
            confirm_diff = lambda _file, _diff_output: True
        else:
            confirm_diff = lambda file, diff_output: interactions.confirm_diff(
                file, diff_output
            )

        edit.apply(confirm_diff)
    except QuitException:
        user_interface.display_message("Canceled")
    finally:
        readline.write_history_file(histfile)


if __name__ == "__main__":
    root_directory = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    sys.path.append(root_directory)

    main()
