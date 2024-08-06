import os
import sys
from navie.log_print import log_print
from navie.editor import Editor


# Utilizes default behaviors to generate and print a solution for an issue.
class SimpleSolver:
    def __init__(self):
        self.temperature = 0.0
        self.token_limit = None
        self.log = log_print

    def solve(self, issue_file, work_dir):
        editor = Editor(work_dir, self.temperature, self.token_limit, self.log)

        with open(issue_file, "r") as f:
            issue_content = f.read()

        editor.plan(issue_content)
        generated_code = editor.generate()

        print(generated_code)


if __name__ == "__main__":
    issue_file = sys.argv[1]
    work_dir = sys.argv[2]

    print(f"Solving issue {issue_file} in {work_dir}")

    if not os.path.exists(issue_file):
        print(f"Error: {issue_file} does not exist")
        sys.exit(1)
    if not os.path.exists(work_dir):
        print(f"Error: {work_dir} does not exist")
        sys.exit(1)

    solver = SimpleSolver()
    solver.solve(issue_file, work_dir)
