#!/usr/bin/env python

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from navie.editor import Editor

work_dir = os.path.join(".appmap", "navie", "work")
log_dir = os.path.join(".appmap", "navie", "log")
issue_file = os.path.join(work_dir, "issue.txt")
if not os.path.exists(issue_file):
    print("Issue file not found")
    sys.exit(1)

with open(issue_file, "r") as f:
    issue = f.read()

editor = Editor(work_dir, log_dir=log_dir)
editor.plan(issue)
