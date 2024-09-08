import os
import time

from navie.config import Config

# EXCLUDE_PYTHON_TESTS_PATTERN = """(\\btesting\\b|\\btest\\b|\\btests\\b|\\btest_|_test\\.py$|\\.txt$|\\.html$|\\.rst$|\\.md$)"""


class Client:

    def __init__(
        self,
        work_dir,
        temperature=None,
        token_limit=None,
        trajectory_file=None,
    ):
        self.work_dir = work_dir
        self.trajectory_file = trajectory_file
        self.temperature = 0.0 if temperature is None else temperature
        self.token_limit = token_limit

    def apply(self, file_path, replace, search=None):
        log_file = os.path.join(self.work_dir, "apply.log")
        search_file = os.path.join(self.work_dir, "search.txt")
        replace_file = os.path.join(self.work_dir, "replace.txt")

        with open(replace_file, "w") as replace_f:
            replace_f.write(replace)

        env = self._prepare_env()
        env_str = " ".join([f"{k}={v}" for k, v in env.items()])

        cmd = f"{env_str} {Config.get_appmap_command()} apply"

        if search is not None:
            with open(search_file, "w") as search_f:
                search_f.write(search)
            cmd += f" -s {search_file}"

        cmd += f" -r {replace_file}"
        cmd += f" {file_path}"
        cmd += f" > {log_file} 2>&1"
        exit_status = self._execute(cmd, log_file)
        return exit_status == 0

    def compute_update(self, file_path, new_content_file, prompt_file=None):
        file_slug = "".join([c if c.isalnum() else "_" for c in file_path]).strip("_")
        log_file = os.path.join(self.work_dir, file_slug, "compute_update.log")
        output_file = os.path.join(self.work_dir, file_slug, "compute_update.txt")

        command = self._build_command(
            input_path=file_path,
            context_path=new_content_file,
            output_path=output_file,
            log_file=log_file,
            prompt_path=prompt_file,
        )
        exit_status = self._execute(command, log_file)
        return exit_status == 0

    def ask(self, question_file, output_file, context_file=None, prompt_file=None):
        log_file = os.path.join(self.work_dir, "ask.log")
        input_file = os.path.join(self.work_dir, "ask.txt")

        with open(question_file, "r") as question_f:
            question = question_f.read()

        with open(input_file, "w") as input_f:
            input_tokens = ["@explain"]
            if context_file:
                input_tokens.append("/nocontext")
            input_tokens.append(question)
            input_f.write(" ".join(input_tokens))

        command = self._build_command(
            input_path=question_file,
            output_path=output_file,
            log_file=log_file,
            prompt_path=prompt_file,
        )
        self._execute(command, log_file)

    def terms(self, issue_file, output_file):
        log_file = os.path.join(self.work_dir, "terms.log")
        input_file = os.path.join(self.work_dir, "terms.txt")
        prompt_file = os.path.join(self.work_dir, "terms.prompt.md")

        with open(issue_file, "r") as issue_f:
            issue_content = issue_f.read()

        with open(input_file, "w") as input_f:
            input_tokens = ["@generate"]
            input_tokens.append("/nocontext")
            input_tokens.append(issue_content)
            input_f.write(" ".join(input_tokens))

        with open(prompt_file, "w") as prompt_f:
            prompt_f.write(
                f"""Generate a list of all file names, module names, class names, function names and varable names that are mentioned in the
described issue. Do not emit symbols that are part of the programming language itself. Do not emit symbols that are part
of test frameworks. Focus on library and application code only. Emit the results as a JSON list. Do not emit text, markdown, 
or explanations.
"""
            )

        command = self._build_command(
            input_path=input_file,
            output_path=output_file,
            log_file=log_file,
            prompt_path=prompt_file,
        )
        self._execute(command, log_file)

    def context(
        self,
        query_file,
        output_file,
        exclude_pattern=None,
        include_pattern=None,
        vectorize_query=True,
    ):
        log_file = os.path.join(self.work_dir, "search_terms.log")

        with open(query_file, "r") as f:
            query_content = f.read()

        question = ["@context /nofence /format=yaml"]
        if not vectorize_query:
            question.append("/noterms")
        if exclude_pattern:
            question.append(f"/exclude={exclude_pattern}")
        if include_pattern:
            question.append(f"/include={include_pattern}")

        question_file = os.path.join(self.work_dir, "context.txt")
        with open(question_file, "w") as apply_f:
            apply_f.write(
                f"""{" ".join(question)}
                        
{query_content}
"""
            )

        command = self._build_command(
            input_path=question_file, output_path=output_file, log_file=log_file
        )
        self._execute(command, log_file)

    def plan(self, issue_file, output_file, context_file=None, prompt_file=None):
        log_file = os.path.join(self.work_dir, "plan.log")
        input_file = os.path.join(self.work_dir, "plan.txt")

        with open(issue_file, "r") as issue_f:
            issue_content = issue_f.read()

        with open(input_file, "w") as plan_f:
            input_tokens = ["@plan"]
            if context_file:
                input_tokens.append("/nocontext")
            input_tokens.append(issue_content)
            plan_f.write(" ".join(input_tokens))

        command = self._build_command(
            input_path=input_file,
            output_path=output_file,
            context_path=context_file,
            prompt_path=prompt_file,
            log_file=log_file,
        )
        self._execute(command, log_file)

    def search(
        self,
        query_file,
        output_file,
        context_file=None,
        prompt_file=None,
        format_file=None,
    ):
        log_file = os.path.join(self.work_dir, "search.log")
        input_file = os.path.join(self.work_dir, "search.txt")

        with open(query_file, "r") as query_f:
            query_content = query_f.read()

        with open(input_file, "w") as search_f:
            input_tokens = ["@search"]
            if context_file:
                input_tokens.append("/nocontext")
            if format_file:
                input_tokens.append(f"/noformat")
            input_tokens.append(query_content)
            input = " ".join(input_tokens)
            search_f.write(input)

        if format_file:
            if not prompt_file:
                prompt_file = format_file
            else:
                # Append format instructions to the prompt
                with open(format_file) as format_f:
                    format = format_f.read()

                with open(prompt_file, "a") as prompt_f:
                    prompt_f.write(
                        f"""

{format}
"""
                    )

        command = self._build_command(
            input_path=input_file,
            output_path=output_file,
            context_path=context_file,
            prompt_path=prompt_file,
            log_file=log_file,
        )
        self._execute(command, log_file)

    def list_files(self, plan_file, output_file):
        log_file = os.path.join(self.work_dir, "list_files.log")
        input_file = os.path.join(self.work_dir, "list_files.txt")

        with open(plan_file, "r") as plan_f:
            plan_content = plan_f.read()

        with open(input_file, "w") as question_f:
            question_f.write(
                f"""@list-files /format=json /nofence
                             
{plan_content}
"""
            )

        command = self._build_command(
            input_path=input_file,
            output_path=output_file,
            log_file=log_file,
        )
        self._execute(command, log_file)

    def generate(
        self,
        plan_file,
        output_file,
        context_file=None,
        prompt_file=None,
    ):
        log_file = os.path.join(self.work_dir, "generate.log")
        input_file = os.path.join(self.work_dir, "generate.txt")

        with open(plan_file, "r") as plan_f:
            plan_content = plan_f.read()
        with open(input_file, "w") as input_f:
            input_tokens = ["@generate"]
            input_tokens.append("/noformat")
            if context_file:
                input_tokens.append("/nocontext")
            input_tokens.append(plan_content)
            input = " ".join(input_tokens)

            input_f.write(input)

        command = self._build_command(
            input_path=input_file,
            output_path=output_file,
            context_path=context_file,
            prompt_path=prompt_file,
            log_file=log_file,
        )
        self._execute(command, log_file)

    def test(
        self,
        issue_file,
        output_file,
        context_file=None,
        prompt_file=None,
    ):
        log_file = os.path.join(self.work_dir, "test.log")
        input_file = os.path.join(self.work_dir, "test.txt")

        with open(issue_file, "r") as issue_f:
            issue_content = issue_f.read()

        with open(input_file, "w") as input_f:
            input_tokens = ["@test", "/noformat"]
            if context_file:
                input_tokens.append("/nocontext")
            input_tokens.append(issue_content)
            input = " ".join(input_tokens)

            input_f.write(input)

        command = self._build_command(
            input_path=input_file,
            output_path=output_file,
            context_path=context_file,
            prompt_path=prompt_file,
            log_file=log_file,
        )
        self._execute(command, log_file)

    def _prepare_env(self):
        env = {}
        if self.temperature is not None:
            env["APPMAP_NAVIE_TEMPERATURE"] = str(self.temperature)
        if self.token_limit is not None:
            env["APPMAP_NAVIE_TOKEN_LIMIT"] = str(self.token_limit)
        return env

    def _build_command(
        self,
        output_path,
        log_file,
        context_path=None,
        input_path=None,
        prompt_path=None,
        additional_args=None,
    ):
        env = self._prepare_env()
        env_str = " ".join([f"{k}={v}" for k, v in env.items()])

        cmd = f"{env_str} {Config.get_appmap_command()} navie --log-navie"
        if input_path:
            cmd += f" -i {input_path}"
        if context_path:
            cmd += f" -c {context_path}"
        if prompt_path:
            cmd += f" -p {prompt_path}"
        if self.trajectory_file:
            cmd += f" --trajectory-file {self.trajectory_file}"
        cmd += f" -o {output_path}"
        if additional_args:
            cmd += f" {additional_args}"
        cmd += f" > {log_file} 2>&1"

        return cmd

    def _execute(self, command, log_file):
        max_retries = 3
        delay = 10
        log_start_line = 0

        for attempt in range(max_retries):
            file_mode = "a" if attempt > 0 else "w"
            with open(log_file, file_mode) as f:
                f.write("$ ")
                f.write(command)
                f.write("\n\n")

            result = os.system(command)

            if result == 0:
                return result

            with open(log_file, "r") as f:
                log_lines = f.readlines() or [""]
                log_content = "\n".join(log_lines[log_start_line:])
                log_start_line = len(log_lines)

                print("\n".join(log_content.split("\n")[-200:]))

            # This can be / is happening with Anthropic
            if "Connection error" in log_content:
                print(f"Connection error on attempt {attempt}.")

                if attempt < max_retries - 1:
                    print(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                    delay *= 1.5
            else:
                break

        # Failed to complete: Connection error
        raise RuntimeError(
            f"Failed to execute command {command}. See {log_file} for details."
        )
