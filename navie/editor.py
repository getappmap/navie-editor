import json
import os
import re
import shutil
import time

import yaml
from navie.config import Config
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

        self._plan = None
        self._context = None

    # Set context
    def set_context(self, context):
        self._context = context

    def apply(self, filename, replace, search=None):
        self._log_action("@apply", filename)

        filename_slug = "".join([c if c.isalnum() else "_" for c in filename]).strip(
            "_"
        )

        work_dir = self._work_dir("apply", filename_slug)
        succeeded = Client(work_dir, self.temperature, self.token_limit).apply(
            filename, replace, search=search
        )
        message = "Changes applied" if succeeded else "Failed to apply changes"
        self._log_response(message)

    def ask(
        self,
        question,
        prompt=None,
        options=None,
        context=None,
        cache=True,
        auto_context=True,
    ):
        self._log_action("@explain", options, question)

        work_dir = self._work_dir("ask")
        input_file = os.path.join(work_dir, "ask.input.txt")
        output_file = os.path.join(work_dir, "ask.md")

        def read_output(save_cache):
            with open(output_file, "r") as f:
                explanation = f.read()

            if save_cache:
                self._save_cache(
                    work_dir,
                    question,
                    "question",
                    options,
                    "options",
                    prompt,
                    "prompt",
                    context,
                    "context",
                )

            self._log_response(explanation, output_file=output_file)

            return explanation

        if cache and self._all_cache_valid(
            work_dir,
            question,
            "question",
            options,
            "options",
            prompt,
            "prompt",
            context,
            "context",
        ):
            print("  Using cached answer")
            return read_output(False)

        with open(input_file, "w") as f:
            content = []
            if options:
                content.append(options)
            content.append(question)
            f.write(" ".join(content))

        context_file = self._save_context(work_dir, "ask", context, auto_context)
        prompt_file = self._save_prompt(work_dir, "ask", prompt)

        Client(work_dir, self.temperature, self.token_limit).ask(
            input_file,
            output_file,
            prompt_file=prompt_file,
            context_file=context_file,
        )

        return read_output(True)

    def suggest_terms(self, question):
        work_dir = self._work_dir("suggest_terms")
        input_file = os.path.join(work_dir, "terms.input.txt")
        output_file = os.path.join(work_dir, "terms.json")

        self._log_action("@generate (terms)", question)

        with open(input_file, "w") as f:
            f.write(question)

        Client(work_dir, self.temperature, self.token_limit).terms(
            input_file, output_file
        )

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
        input_file = os.path.join(work_dir, "context.input.txt")
        output_file = os.path.join(work_dir, "context.yaml")

        self._log_action("@context", options, query)

        def read_output(save_cache):
            with open(output_file, "r") as f:
                raw_context = f.read()
                context = yaml.safe_load("\n".join(extract_fenced_content(raw_context)))

            if save_cache:
                self._save_cache(
                    work_dir,
                    query,
                    "query",
                    options,
                    "options",
                    vectorize_query,
                    "vectorize",
                    exclude_pattern,
                    "exclude",
                    include_pattern,
                    "include",
                )

            self._context = context

            self._log_response(raw_context, output_file=output_file)

            return context

        if cache and self._all_cache_valid(
            work_dir,
            query,
            "query",
            options,
            "options",
            vectorize_query,
            "vectorize",
            exclude_pattern,
            "exclude",
            include_pattern,
            "include",
        ):
            print("  Using cached context")
            return read_output(False)

        with open(input_file, "w") as f:
            content = []
            if options:
                content.append(options)
            content.append(query)
            f.write(" ".join(content))

        Client(work_dir, self.temperature, self.token_limit).context(
            input_file, output_file, exclude_pattern, include_pattern, vectorize_query
        )

        return read_output(True)

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

        def read_output(save_cache):
            with open(output_file, "r") as f:
                self._plan = f.read()

            if save_cache:
                self._save_cache(
                    work_dir,
                    issue,
                    "issue",
                    options,
                    "options",
                    context,
                    "context",
                    prompt,
                    "prompt",
                )

            print(f"  Output is available at {output_file}")

            self._log_response(self._plan, output_file=output_file)

            return self._plan

        if cache and self._all_cache_valid(
            work_dir,
            issue,
            "issue",
            options,
            "options",
            context,
            "context",
            prompt,
            "prompt",
        ):
            print("  Using cached plan")
            return read_output(False)

        with open(issue_file, "w") as f:
            content = []
            if options:
                content.append(options)
            content.append(issue)
            f.write(" ".join(content))

        context_file = self._save_context(work_dir, "plan", context, auto_context)
        prompt_file = self._save_prompt(work_dir, "plan", prompt)

        Client(work_dir, self.temperature, self.token_limit).plan(
            issue_file, output_file, context_file, prompt_file=prompt_file
        )

        return read_output(True)

    def list_files(self, content):
        # Scan through all the files in the content and look for file-ish regepx patterns.
        # Select the ones that match up to real, existing files.

        self._log_action("list-files", content)

        path_separator = os.path.sep
        path_separator_escaped = re.escape(path_separator)
        file_regexp = (
            r"([a-zA-Z0-9_" + path_separator_escaped + r"\-]+\.(?:[a-zA-Z0-9]{1,4}))\b"
        )

        files = list(set(re.findall(file_regexp, content)))
        print(f"Path-like strings in content: {files}")
        existing_files = [f for f in files if os.path.exists(f)]
        print(f"File paths that exist on the filesystem: {existing_files}")

        self._log_response(", ".join(existing_files))

        return existing_files

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
        plan_file = os.path.join(work_dir, "generate.input.txt")
        output_file = os.path.join(work_dir, "generate.md")

        if not plan:
            if not self._plan:
                raise ValueError("No plan provided or generated")
            plan = self._plan

        if not context:
            context = self._context

        self._log_action("@generate", options, plan)

        def read_output(save_cache):
            with open(output_file, "r") as f:
                code = f.read()

            if save_cache:
                self._save_cache(
                    work_dir,
                    plan,
                    "plan",
                    options,
                    "options",
                    context,
                    "context",
                    prompt,
                    "prompt",
                )

            print(f"  Output is available at {output_file}")

            self._log_response(code, output_file=output_file)

            return code

        if cache and self._all_cache_valid(
            work_dir,
            plan,
            "plan",
            options,
            "options",
            context,
            "context",
            prompt,
            "prompt",
        ):
            print("  Using cached generated code")
            return read_output(False)

        with open(plan_file, "w") as f:
            content = []
            if options:
                content.append(options)
            content.append(plan)
            f.write(" ".join(content))

        context_file = self._save_context(work_dir, "generate", context, auto_context)
        prompt_file = self._save_prompt(work_dir, "generate", prompt)

        Client(work_dir, self.temperature, self.token_limit).generate(
            plan_file,
            output_file,
            context_file=context_file,
            prompt_file=prompt_file,
        )

        return read_output(True)

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
        input_file = os.path.join(work_dir, "search.input.txt")
        output_file = os.path.join(work_dir, f"search.output.{extension}")

        self._log_action("@search", options, query)

        def read_output(save_cache):
            with open(output_file, "r") as f:
                search_results = f.read()

            if save_cache:
                self._save_cache(
                    work_dir,
                    query,
                    "query",
                    options,
                    "options",
                    context,
                    "context",
                    prompt,
                    "prompt",
                    format,
                    "format",
                )

            print(f"  Output is available at {output_file}")

            self._log_response(search_results, output_file=output_file)

            return search_results

        if cache and self._all_cache_valid(
            work_dir,
            query,
            "query",
            options,
            "options",
            context,
            "context",
            prompt,
            "prompt",
            format,
            "format",
        ):
            print("  Using cached search results")
            return read_output(False)

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

        Client(work_dir, self.temperature, self.token_limit).search(
            input_file,
            output_file,
            context_file=context_file,
            prompt_file=prompt_file,
            format_file=format_file,
        )

        return read_output(True)

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
        issue_file = os.path.join(work_dir, "test.input.txt")
        output_file = os.path.join(work_dir, "test.md")

        if not context:
            context = self._context

        self._log_action("@test", options, issue)

        def read_output(save_cache):
            with open(output_file, "r") as f:
                code = f.read()

            if save_cache:
                self._save_cache(
                    work_dir,
                    issue,
                    "issue",
                    options,
                    "options",
                    context,
                    "context",
                    prompt,
                    "prompt",
                )

            print(f"  Output is available at {output_file}")

            self._log_response(code, output_file=output_file)

            return code

        if cache and self._all_cache_valid(
            work_dir,
            issue,
            "issue",
            options,
            "options",
            context,
            "context",
            prompt,
            "prompt",
        ):
            print("  Using cached test case")
            return read_output(False)

        with open(issue_file, "w") as f:
            content = []
            if options:
                content.append(options)
            content.append(issue)
            f.write(" ".join(content))

        context_file = self._save_context(work_dir, "test", context, auto_context)
        prompt_file = self._save_prompt(work_dir, "test", prompt)

        Client(work_dir, self.temperature, self.token_limit).test(
            issue_file,
            output_file,
            context_file=context_file,
            prompt_file=prompt_file,
        )

        return read_output(True)

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

            if len(files > 0):
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
