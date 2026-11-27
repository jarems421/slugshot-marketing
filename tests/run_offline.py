"""Run the project's offline unittest suites and the two pinned scholarly suites."""

import argparse
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHOLARLY = ("verifying-bibliography", "surveying-literature")


def run_skill(skill):
    """Run an upstream suite with the one Windows-incompatible assertion skipped."""
    directory = ROOT / ".claude" / "skills" / skill / "assets" / "tests"
    os.chdir(directory)
    suite = unittest.defaultTestLoader.discover(str(directory))
    if os.name == "nt" and skill == "surveying-literature":
        from test_main_tex import TestMainTex

        TestMainTex.test_absolute_main_is_kept = unittest.skip(
            "expects POSIX absolute-path syntax; Windows resolves the path with a drive letter"
        )(TestMainTex.test_absolute_main_is_kept)
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1


def main(argv=None):
    """Run each suite in its own process to isolate fixture state."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill", choices=SCHOLARLY)
    args = parser.parse_args(argv)
    if args.skill:
        return run_skill(args.skill)

    environment = {
        **os.environ,
        "PYTHONUTF8": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "SLUGSHOT_TEST_SKIP_MEDIA": "1",
    }
    status = 0
    for path in sorted((ROOT / "tests").glob("test_*.py")):
        module = f"tests.{path.stem}"
        print(f"\n{module}", flush=True)
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "-v", module], cwd=ROOT, env=environment
        )
        status |= bool(result.returncode)
    for skill in SCHOLARLY:
        print(f"\n{skill}", flush=True)
        result = subprocess.run(
            [sys.executable, __file__, "--skill", skill], cwd=ROOT, env=environment
        )
        status |= bool(result.returncode)
    return status


if __name__ == "__main__":
    sys.exit(main())
