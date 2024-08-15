import unittest
from unittest.mock import Mock, patch, mock_open
from navie.mode.interactions import Interactions
from navie.mode.quit_exception import QuitException

class TestInteractions(unittest.TestCase):
    def setUp(self):
        self.mock_user_interface = Mock()
        self.interactions = Interactions(self.mock_user_interface)

    def test_enter_to_continue_quit(self):
        self.mock_user_interface.get_input.return_value = "q"
        with self.assertRaises(QuitException):
            self.interactions.enter_to_continue()
        self.mock_user_interface.get_input.assert_called_once_with("Press enter to continue (or 'q' to quit):")

    def test_enter_to_continue_continue(self):
        self.mock_user_interface.get_input.return_value = "\n"
        try:
            self.interactions.enter_to_continue()
        except QuitException:
            self.fail("enter_to_continue() raised QuitException unexpectedly!")
        self.mock_user_interface.get_input.assert_called_once_with("Press enter to continue (or 'q' to quit):")

    @patch("tempfile.NamedTemporaryFile", mock_open())
    @patch("builtins.open", new_callable=mock_open, read_data="updated problem statement")
    @patch("os.remove")
    def test_prompt_user_for_adjustments(self, mock_file, mock_remove):
        problem_statement = "initial problem statement"
        self.interactions.user_interface.open_editor = Mock()

        result = self.interactions.prompt_user_for_adjustments(problem_statement)

        # Check that the problem statement was written to the temporary file
        mock_file().write.assert_called_once_with(problem_statement.encode("utf-8"))

        # Check that the editor was opened with the correct file path
        self.interactions.user_interface.open_editor.assert_called_once()

        # Check that the updated problem statement was read from the file
        self.assertEqual(result, "updated problem statement")

        # Ensure os.remove was called with the correct file path
        mock_remove.assert_called_once_with(mock_file().name)

if __name__ == "__main__":
    unittest.main()
