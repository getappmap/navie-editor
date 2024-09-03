import os
import hashlib
import json
from pathlib import Path
from typing import Callable, Union


def with_cache(
    work_dir: str, implementation_func: Callable[[], Union[str, dict]], **kwargs
) -> Union[str, dict]:
    def compute_hash():
        hasher = hashlib.sha256()
        hasher.update(json.dumps(kwargs, sort_keys=True).encode("utf-8"))
        return hasher.hexdigest()

    cache_file = Path(os.path.join(work_dir, "cache.json"))
    cache_key = compute_hash()

    if cache_file.exists():
        with cache_file.open("r") as f:
            cache = json.load(f)
        if cache.get("key") == cache_key:
            return cache["result"]

    result = implementation_func()

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "w") as f:
        json.dump({"key": cache_key, "result": result}, f)

    return result


if __name__ == "__main__":
    work_dir = os.path.join(os.path.dirname(__file__), "work")
    x = 1
    y = 2
    with_cache(work_dir, lambda: str(x + y), x=1, y=2)
