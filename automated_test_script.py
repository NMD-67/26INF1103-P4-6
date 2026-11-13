"""Compatibility command for the maintained offline CI suite."""
from pathlib import Path
import runpy

if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "ci" / "offline_tests.py"
    runpy.run_path(str(target), run_name="__main__")
