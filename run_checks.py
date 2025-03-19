#!/usr/bin/env python3
"""
Utility script to run all code quality checks and tests in one go.
"""

import os
import subprocess
import sys
from typing import List, Tuple

# Colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"
YELLOW = "\033[93m"
CYAN = "\033[96m"


def run_command(command: List[str], description: str) -> Tuple[bool, str]:
    """Run a shell command and return the result."""
    print(f"{CYAN}Running {description}...{RESET}")
    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT).decode("utf-8")
        print(f"{GREEN}✓ {description} passed{RESET}")
        return True, output
    except subprocess.CalledProcessError as e:
        print(f"{RED}✗ {description} failed{RESET}")
        return False, e.output.decode("utf-8")


def main() -> int:
    """Run all checks and tests."""
    all_passed = True
    results = []

    # Format with black
    success, output = run_command(["black", "--check", "."], "Black code formatting")
    results.append(("Black", success, output))
    all_passed = all_passed and success

    # Sort imports with isort
    success, output = run_command(["isort", "--check", "."], "isort import sorting")
    results.append(("isort", success, output))
    all_passed = all_passed and success

    # Lint with flake8
    success, output = run_command(["flake8", "src", "tests"], "flake8 linting")
    results.append(("flake8", success, output))
    all_passed = all_passed and success

    # Type check with mypy
    success, output = run_command(["mypy", "src"], "mypy type checking")
    results.append(("mypy", success, output))
    all_passed = all_passed and success

    # Run tests with coverage
    success, output = run_command(
        ["pytest", "--cov=src", "--cov-report=term", "--cov-report=html"], "pytest with coverage"
    )
    results.append(("pytest", success, output))
    all_passed = all_passed and success

    # Print summary
    print("\n" + "=" * 50)
    print(f"{CYAN}SUMMARY:{RESET}")
    for name, success, _ in results:
        status = f"{GREEN}PASSED{RESET}" if success else f"{RED}FAILED{RESET}"
        print(f"{name}: {status}")

    # Print detailed outputs for failed checks
    if not all_passed:
        print("\n" + "=" * 50)
        print(f"{YELLOW}DETAILS OF FAILED CHECKS:{RESET}")
        for name, success, output in results:
            if not success:
                print(f"\n{CYAN}{name} output:{RESET}")
                print(output)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
