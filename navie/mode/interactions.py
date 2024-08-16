import os
import tempfile

from .quit_exception import QuitException
from .user_interface import UserInterface


class Interactions:
    def __init__(self, user_interface):
        self.user_interface = user_interface

    def enter_to_continue(self):
        confirmation = self.user_interface.get_input(
            "Press enter to continue (or 'q' to quit): "
        )
        if confirmation.lower() == "q":
            raise QuitException()

    def collect_problem_statement(self) -> str:
        return self.user_interface.open_editor_and_read()

    def prompt_user_for_adjustments(self, problem_statement: str) -> str:
        return self.user_interface.open_editor_and_read(problem_statement)

    def confirm_diff(self, file: str, diff_output: str) -> bool:
        self.user_interface.display_message(f"Diff for file {file}:")
        colored_diff_output = self.colorize_diff(diff_output)
        self.user_interface.display_message(colored_diff_output)
        try:
            apply_changes_str = self.user_interface.get_input(
                "Do you want to apply the changes? (y/n/q): "
            )
            if apply_changes_str.lower() == "q":
                raise QuitException()

            return apply_changes_str.lower() == "y"
        except EOFError:
            pass

        return False

    def colorize_diff(self, diff_output: str) -> str:
        colored_diff = []
        for line in diff_output.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                colored_diff.append(UserInterface.colorize(line, "green"))
            elif line.startswith("-") and not line.startswith("---"):
                colored_diff.append(UserInterface.colorize(line, "red"))
            else:
                colored_diff.append(line)
        return "\n".join(colored_diff)
