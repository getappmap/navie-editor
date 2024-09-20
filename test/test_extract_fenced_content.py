import unittest

from navie.fences import extract_fenced_content, trim_single_backticks


class TestFenceFunctions(unittest.TestCase):
    def test_extract_fenced_content(self):
        content_with_fences = """
```python
print('Hello, world!')
```
"""
        content_without_fences = """
print('Hello, world!')
"""
        content_multiple_fences = """```python
print('Hello, world!')
```
```python
print('Goodbye, world!')
```
"""

        self.assertEqual(
            extract_fenced_content(content_with_fences), ["print('Hello, world!')\n"]
        )
        self.assertEqual(
            extract_fenced_content(content_without_fences),
            ["\nprint('Hello, world!')\n"],
        )
        self.assertEqual(
            extract_fenced_content(content_multiple_fences),
            ["print('Hello, world!')\n", "print('Goodbye, world!')\n"],
        )

    def test_mixed_markdown_content(self):
        content = """
<!-- file: /home/runner/work/navie-benchmark/navie-benchmark/solve/astropy__astropy-12907/source/astropy/modeling/tests/test_compound_separability.py -->
```python
import pytest
import numpy as np
from astropy.modeling import models
from astropy.modeling.separable import separability_matrix

def test_nested_compound_model_separability():
    # Define the compound model
    cm = models.Linear1D(10) & models.Linear1D(5)
```
"""
        self.assertEqual(
            extract_fenced_content(content),
            [
                """import pytest
import numpy as np
from astropy.modeling import models
from astropy.modeling.separable import separability_matrix

def test_nested_compound_model_separability():
    # Define the compound model
    cm = models.Linear1D(10) & models.Linear1D(5)
"""
            ],
        )

    def test_trim_single_backticks(self):
        self.assertEqual(trim_single_backticks("`hello`"), "hello")
        self.assertEqual(trim_single_backticks("hello"), "hello")
        self.assertEqual(trim_single_backticks("`hello"), "`hello")
        self.assertEqual(trim_single_backticks("hello`"), "hello`")

    def test_trim_single_backticks_from_fenced_content(self):
        content = """`hello`"""
        self.assertEqual(extract_fenced_content(content), ["hello"])


if __name__ == "__main__":
    unittest.main()
