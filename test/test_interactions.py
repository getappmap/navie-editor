import unittest
from unittest.mock import Mock, patch, mock_open
from navie.mode.interactions import Interactions
from navie.mode.quit_exception import QuitException
from navie.mode.user_interface import UserInterface


class TestInteractions(unittest.TestCase):
    def setUp(self):
        self.mock_user_interface = Mock()
        self.interactions = Interactions(self.mock_user_interface)

    def test_enter_to_continue_quit(self):
        self.mock_user_interface.get_input.return_value = "q"
        with self.assertRaises(QuitException):
            self.interactions.enter_to_continue()
        self.mock_user_interface.get_input.assert_called_once_with(
            "Press enter to continue (or 'q' to quit):"
        )

    def test_enter_to_continue_continue(self):
        self.mock_user_interface.get_input.return_value = "\n"
        try:
            self.interactions.enter_to_continue()
        except QuitException:
            self.fail("enter_to_continue() raised QuitException unexpectedly!")
        self.mock_user_interface.get_input.assert_called_once_with(
            "Press enter to continue (or 'q' to quit):"
        )

    def test_collect_problem_statement(self):
        self.mock_user_interface.open_editor_and_read.return_value = "problem statement"
        self.assertEqual(
            self.interactions.collect_problem_statement(), "problem statement"
        )
        self.mock_user_interface.open_editor_and_read.assert_called_once()

    def test_prompt_user_for_adjustments(self):
        problem_statement = "initial problem statement"
        self.interactions.user_interface.open_editor = Mock()
        self.interactions.prompt_user_for_adjustments(problem_statement)
        self.interactions.user_interface.open_editor_and_read.assert_called_once()

    def test_confirm_diff_apply(self):
        self.mock_user_interface.get_input.return_value = "y"
        self.assertTrue(self.interactions.confirm_diff("the-file", "diff output"))
        self.mock_user_interface.display_message.assert_any_call(
            "Diff for file the-file:"
        )
        self.mock_user_interface.get_input.assert_called_once_with(
            "Do you want to apply the changes? (y/n/q)"
        )

    def test_confirm_diff_quit(self):
        self.mock_user_interface.get_input.return_value = "q"
        with self.assertRaises(QuitException):
            self.interactions.confirm_diff("the-file", "diff output")
        self.mock_user_interface.display_message.assert_any_call(
            "Diff for file the-file:"
        )
        self.mock_user_interface.get_input.assert_called_once_with(
            "Do you want to apply the changes? (y/n/q)"
        )

    def test_colorize_diff(self):
        diff_output = """- line 1
+ line 2
line 3"""
        self.assertEqual(
            self.interactions.colorize_diff(diff_output),
            "\n".join(
                [
                    UserInterface.colorize("- line 1", "red"),
                    UserInterface.colorize("+ line 2", "green"),
                    "line 3",
                ]
            ),
        )


if __name__ == "__main__":
    unittest.main()
