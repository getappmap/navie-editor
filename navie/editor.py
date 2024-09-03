import json
import os
import re
import shutil
import time

import yaml
from navie.config import Config
from navie.with_cache import with_cache
from navie.fences import extract_fenced_content
from navie.client import Client


class Editor:

    def __init__(
        self,
        work_dir,
        temperature=None,  # Can also be configured via the APPMAP_NAVIE_TEMPERATURE environment variable
        token_limit=None,  # Can also be configured via the APPMAP_NAVIE_TOKEN_LIMIT environment variable
        log_dir=None,
        log=None,
        clean=Config.get_clean(),
        trajectory_file=Config.get_trajectory_file(),
    ):
        self.work_dir = work_dir
        os.makedirs(self.work_dir, exist_ok=True)

        self.temperature = temperature
        self.token_limit = token_limit
        if log:
            self.log = log
        else:
            log_dir = log_dir or self.work_dir
            log_file = os.path.join(log_dir, "navie.log")
            log_file_lock = os.path.join(log_dir, "navie.log.lock")

            os.makedirs(log_dir, exist_ok=True)

            def log_message(msg):
                with open(log_file_lock, "w"):
                    with open(log_file, "a") as log_file_handle:
                        log_file_handle.write(msg + "\n")

            self.log = log_message
        self.clean = clean
        self.trajectory_file = trajectory_file

        self._plan = None
        self._context = None

    def sub_editor(self, work_dir):
        """
        Create a new Editor instance with a subdirectory of the current work directory.
        All other settings will be inherited from the current Editor instance.

        :param work_dir: The name of the subdirectory to create.
        """
        return Editor(
            os.path.join(self.work_dir, work_dir),
            temperature=self.temperature,
            token_limit=self.token_limit,
            log_dir=os.path.dirname(work_dir),
            log=self.log,
            clean=self.clean,
            trajectory_file=self.trajectory_file,
        )

    # Set context
    def set_context(self, context):
        self._context = context

    def apply(self, filename, replace, search=None):
        self._log_action("@apply", filename)

        filename_slug = "".join([c if c.isalnum() else "_" for c in filename]).strip(
            "_"
        )

        work_dir = self._work_dir("apply", filename_slug)
        succeeded = self._build_client(work_dir).apply(filename, replace, search=search)
        message = "Changes applied" if succeeded else "Failed to apply changes"
        self._log_response(message)

    def ask(
        self,
        question,
        question_name="ask",
        prompt=None,
        options=None,
        context=None,
        cache=True,
        auto_context=True,
    ):
        self._log_action("@explain", options, question)
        work_dir = self._work_dir(question_name)

        def _ask() -> str:
            input_file = os.path.join(work_dir, f"ask.input.txt")
            output_file = os.path.join(work_dir, "ask.md")

            with open(input_file, "w") as f:
                content = []
                if options:
                    content.append(options)
                content.append(question)
                f.write(" ".join(content))

            context_file = self._save_context(work_dir, "ask", context, auto_context)
            prompt_file = self._save_prompt(work_dir, "ask", prompt)

            self._build_client(work_dir).ask(
                input_file,
                output_file,
                prompt_file=prompt_file,
                context_file=context_file,
            )

            with open(output_file, "r") as f:
                return f.read()

        return (
            with_cache(
                work_dir,
                _ask,
                question=question,
                question_name=question_name,
                prompt=prompt,
                options=options,
                context=context,
            )
            if cache
            else _ask()
        )

    def suggest_terms(self, question):
        work_dir = self._work_dir("suggest_terms")
        input_file = os.path.join(work_dir, "terms.input.txt")
        output_file = os.path.join(work_dir, "terms.json")

        self._log_action("@generate (terms)", question)

        with open(input_file, "w") as f:
            f.write(question)

        self._build_client(work_dir).terms(input_file, output_file)

        with open(output_file, "r") as f:
            raw_terms = f.read()
            terms = extract_fenced_content(raw_terms)

        self._log_response("\n".join(terms), output_file=output_file)

        return terms

    def context(
        self,
        query,
        options=None,
        vectorize_query=True,
        exclude_pattern=None,
        include_pattern=None,
        cache=True,
    ):
        work_dir = self._work_dir("context")

        self._log_action("@context", options, query)

        def _context() -> dict:
            input_file = os.path.join(work_dir, "context.input.txt")
            output_file = os.path.join(work_dir, "context.yaml")

            with open(input_file, "w") as f:
                content = []
                if options:
                    content.append(options)
                content.append(query)
                f.write(" ".join(content))

            self._build_client(work_dir).context(
                input_file,
                output_file,
                exclude_pattern,
                include_pattern,
                vectorize_query,
            )

            with open(output_file, "r") as f:
                raw_context = f.read()
                context = yaml.safe_load("\n".join(extract_fenced_content(raw_context)))

            return context

        self._context = (
            with_cache(
                work_dir,
                _context,
                query=query,
                options=options,
                vectorize_query=vectorize_query,
                exclude_pattern=exclude_pattern,
                include_pattern=include_pattern,
            )
            if cache
            else _context()
        )

        return self._context

    def plan(
        self,
        issue,
        context=None,
        options=None,
        prompt=None,
        cache=True,
        auto_context=True,
    ):
        work_dir = self._work_dir("plan")
        issue_file = os.path.join(work_dir, "plan.input.txt")
        output_file = os.path.join(work_dir, "plan.md")

        self._log_action("@plan", options, issue)

        def _plan():
            with open(issue_file, "w") as f:
                content = []
                if options:
                    content.append(options)
                content.append(issue)
                f.write(" ".join(content))

            context_file = self._save_context(work_dir, "plan", context, auto_context)
            prompt_file = self._save_prompt(work_dir, "plan", prompt)

            self._build_client(work_dir).plan(
                issue_file, output_file, context_file, prompt_file=prompt_file
            )

            with open(output_file, "r") as f:
                return f.read()

        self._plan = (
            with_cache(
                work_dir,
                _plan,
                issue=issue,
                options=options,
                context=context,
                prompt=prompt,
            )
            if cache
            else _plan()
        )

        return self._plan

    def list_files(self, content):
        # Scan through all the files in the content and look for file-ish regepx patterns.
        # Select the ones that match up to real, existing files.

        self._log_action("list-files", content)

        path_separator = os.path.sep
        path_separator_escaped = re.escape(path_separator)
        file_regexp = (
            r"([a-zA-Z0-9_" + path_separator_escaped + r"\-]+\.(?:[a-zA-Z0-9]{1,4}))\b"
        )

        detected_files = re.findall(file_regexp, content)
        # print(f"Path-like strings in content: {detected_files}")

        absolute_files = [os.path.abspath(f) for f in detected_files]
        unique_files = list(set(absolute_files))
        existing_files = [f for f in unique_files if os.path.exists(f)]
        files = [os.path.relpath(f) for f in existing_files]

        # print(f"File paths that exist on the filesystem: {files}")
        self._log_response(", ".join(files))

        return files

    def generate(
        self,
        plan=None,
        options=None,
        context=None,
        auto_context=True,
        prompt=None,
        cache=True,
    ):
        work_dir = self._work_dir("generate")

        if not plan:
            if not self._plan:
                raise ValueError("No plan provided or generated")
            plan = self._plan

        if not context:
            context = self._context

        self._log_action("@generate", options, plan)

        def _generate():
            plan_file = os.path.join(work_dir, "generate.input.txt")
            output_file = os.path.join(work_dir, "generate.md")

            with open(plan_file, "w") as f:
                content = []
                if options:
                    content.append(options)
                content.append(plan)
                f.write(" ".join(content))

            context_file = self._save_context(
                work_dir, "generate", context, auto_context
            )
            prompt_file = self._save_prompt(work_dir, "generate", prompt)

            self._build_client(work_dir).generate(
                plan_file,
                output_file,
                context_file=context_file,
                prompt_file=prompt_file,
            )

            with open(output_file, "r") as f:
                return f.read()

        return (
            with_cache(
                work_dir,
                _generate,
                plan=plan,
                options=options,
                context=context,
                prompt=prompt,
            )
            if cache
            else _generate()
        )

    def search(
        self,
        query,
        context=None,
        format=None,
        options=None,
        prompt=None,
        cache=True,
        extension="yaml",
        auto_context=True,
    ):
        work_dir = self._work_dir("search")

        self._log_action("@search", options, query)

        def _search():
            input_file = os.path.join(work_dir, "search.input.txt")
            output_file = os.path.join(work_dir, f"search.output.{extension}")

            with open(input_file, "w") as f:
                content = []
                if options:
                    content.append(options)
                content.append(query)
                f.write(" ".join(content))

            context_file = self._save_context(work_dir, "search", context, auto_context)
            prompt_file = self._save_prompt(work_dir, "search", prompt)

            if format:
                format_file = os.path.join(work_dir, "search.format.txt")
                with open(format_file, "w") as f:
                    f.write(format)
            else:
                format_file = None

            self._build_client(work_dir).search(
                input_file,
                output_file,
                context_file=context_file,
                prompt_file=prompt_file,
                format_file=format_file,
            )

            with open(output_file, "r") as f:
                return f.read()

        return (
            with_cache(
                work_dir,
                _search,
                query=query,
                options=options,
                context=context,
                prompt=prompt,
                format=format,
            )
            if cache
            else _search()
        )

    def test(
        self,
        issue,
        context=None,
        options=None,
        auto_context=True,
        prompt=None,
        cache=True,
    ):
        work_dir = self._work_dir("test")

        if not context:
            context = self._context

        self._log_action("@test", options, issue)

        def _test():
            issue_file = os.path.join(work_dir, "test.input.txt")
            output_file = os.path.join(work_dir, "test.md")
            with open(issue_file, "w") as f:
                content = []
                if options:
                    content.append(options)
                content.append(issue)
                f.write(" ".join(content))

            context_file = self._save_context(work_dir, "test", context, auto_context)
            prompt_file = self._save_prompt(work_dir, "test", prompt)

            self._build_client(work_dir).test(
                issue_file,
                output_file,
                context_file=context_file,
                prompt_file=prompt_file,
            )

            with open(output_file, "r") as f:
                return f.read()

        return (
            with_cache(
                work_dir,
                _test,
                issue=issue,
                options=options,
                context=context,
                prompt=prompt,
            )
            if cache
            else _test()
        )

    def _build_client(self, work_dir):
        return Client(
            work_dir, self.temperature, self.token_limit, self.trajectory_file
        )

    def _log_action(self, action, *messages):
        combined_message = " ".join([m for m in messages if m is not None and m != ""])
        clean_content = re.sub(r"[\r\n\t\x0b\x0c]", " ", combined_message)
        clean_content = re.sub(r" +", " ", clean_content)
        if len(clean_content) > 200:
            clean_content = clean_content[:100] + "..."
        self.log(f"{action} {clean_content}")

    def _log_response(self, response, output_file=None):
        clean_content = re.sub(r"[\r\n\t\x0b\x0c]", " ", response)
        clean_content = re.sub(r" +", " ", clean_content)
        if len(clean_content) > 200:
            clean_content = clean_content[:100] + "..."

        if output_file:
            self.log(f"  {output_file}")
        self.log(f"  {clean_content}")

    def _save_context(self, work_dir, name, context, auto_context):
        if context:
            context_file = os.path.join(work_dir, f"{name}.context.yaml")
            if not isinstance(context, str):
                context = yaml.dump(context)

            with open(context_file, "w") as f:
                f.write(context)
        else:
            if not auto_context:
                raise ValueError(
                    "No context provided is available, and auto_context is disabled"
                )
            context_file = None

        return context_file

    def _save_prompt(self, work_dir, name, prompt):
        if prompt:
            prompt_file = os.path.join(work_dir, f"{name}.prompt.md")
            with open(prompt_file, "w") as f:
                f.write(prompt)
        else:
            prompt_file = None

        return prompt_file

    def _save_cache(self, work_dir, *contents):
        # Enumerate the contents in pairs. The first item is the content, and the second item is the content name.
        for i in range(0, len(contents), 2):
            content = contents[i]
            if content is None:
                content = ""
            if not isinstance(content, str):
                content = json.dumps(content)
            content_name = contents[i + 1]
            cache_file = os.path.join(work_dir, f"{content_name}.cache")
            with open(cache_file, "w") as f:
                f.write(content)

    def _all_cache_valid(self, work_dir, *contents):
        # Enumerate the contents in pairs. The first item is the content, and the second item is the content name.
        # Return true if all content caches are valid, otherwise return false.
        for i in range(0, len(contents), 2):
            content = contents[i]
            if content is None:
                content = ""
            if not isinstance(content, str):
                content = json.dumps(content)

            content_name = contents[i + 1]
            if not self._is_cache_valid(work_dir, content, content_name):
                return False

        return True

    def _is_cache_valid(self, work_dir, content, content_name):
        cache_file = os.path.join(work_dir, f"{content_name}.cache")
        if not os.path.exists(cache_file):
            return False

        with open(cache_file, "r") as f:
            cached_content = f.read()
            return cached_content == content

    def _work_dir(self, *name_tokens):
        rename_existing = self.clean

        name = os.path.sep.join(name_tokens)
        work_dir = os.path.join(self.work_dir, name)
        if rename_existing and os.path.exists(work_dir):
            # Rename the existing work dir according to the timestamp of the oldest file in the directory
            files = [
                os.path.join(work_dir, f)
                for f in os.listdir(work_dir)
                if os.path.isfile(os.path.join(work_dir, f))
            ]

            if len(files) > 0:
                # Get the oldest file's timestamp
                oldest_file = min(files, key=os.path.getctime)
                oldest_timestamp = time.strftime(
                    "%Y%m%d%H%M%S", time.gmtime(os.path.getctime(oldest_file))
                )
                new_name = f"{work_dir}_{oldest_timestamp}"
                print(f"Renaming existing work dir to {new_name}")
                shutil.move(work_dir, new_name)
            else:
                print(f"Removing empty work dir {work_dir}")
                shutil.rmtree(work_dir)

        os.makedirs(work_dir, exist_ok=True)
        return work_dir
