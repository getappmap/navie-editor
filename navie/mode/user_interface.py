import os
import subprocess
import tempfile


class UserInterface:
    def get_input(self, prompt: str) -> str:
        return input(prompt)

    def get_confirmation(self, prompt: str) -> bool:
        response = input(prompt).strip().lower()
        return response == "y"

    def display_message(self, message: str, color=None):
        print(UserInterface.colorize(message, color))

    def open_editor_and_read(self, file_content: str = "") -> str:
        with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False) as temp_file:
            temp_file.write(file_content.encode("utf-8"))
            temp_file_path = temp_file.name

        self.open_editor(temp_file_path)

        try:
            with open(temp_file_path, "r", encoding="utf-8") as temp_file:
                result = temp_file.read().strip()
        except Exception as e:
            self.display_message(
                UserInterface.colorize(
                    f"Failed to read the temporary file: {e}", "yellow"
                )
            )
            result = ""
        finally:
            os.remove(temp_file_path)

        return result

    def open_editor(self, file_path: str):
        editor = os.getenv("EDITOR", "nano")
        try:
            subprocess.run([editor, file_path])
        except Exception as e:
            print(f"Failed to open editor: {e}")

    @staticmethod
    def colorize(message: str, color: str) -> str:
        return "".join(
            [UserInterface.begin_color(color), message, UserInterface.end_color(color)]
        )

    @staticmethod
    def begin_color(color: str) -> str:
        if color == "red":
            return "\033[91m"
        elif color == "green":
            return "\033[92m"
        elif color == "white":
            return "\033[97m"
        elif color == "yellow":
            return "\033[93m"
        else:
            return ""

    @staticmethod
    def end_color(color: str) -> str:
        if color:
            return "\033[0m"
        else:
            return ""
