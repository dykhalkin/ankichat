#!/usr/bin/env python3
"""
Script to run code quality checks.
"""

import argparse
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


def format_code():
    """Format code with black and isort."""
    print(f"{CYAN}=== Code Formatting ==={RESET}")
    success1, _ = run_command(["black", "."], "black code formatting")
    success2, _ = run_command(["isort", "."], "isort import sorting")
    return success1 and success2


def run_linting():
    """Run flake8 linting."""
    print(f"{CYAN}=== Code Linting ==={RESET}")
    success, output = run_command(["flake8", "src", "tests"], "flake8 linting")
    if not success:
        print(f"{RED}Linting issues:{RESET}")
        print(output)
    return success


def run_type_checking():
    """Run mypy type checking."""
    print(f"{CYAN}=== Type Checking ==={RESET}")
    success, output = run_command(["mypy", "src"], "mypy type checking")
    if not success:
        print(f"{RED}Type checking issues:{RESET}")
        print(output)
    return success


def run_tests(args):
    """Run tests with pytest, optionally with coverage."""
    print(f"{CYAN}=== Running Tests ==={RESET}")

    pytest_args = ["pytest"]

    # Add verbosity
    if args.verbose:
        pytest_args.append("-v")

    # Add coverage
    if args.coverage:
        pytest_args.extend(["--cov=src", "--cov-report=term", "--cov-report=html"])

    # Add specific test files or directories
    if args.test_path:
        pytest_args.extend(args.test_path)

    success, output = run_command(pytest_args, "running tests")
    if not success:
        print(f"{RED}Test failures:{RESET}")
        print(output)
    elif args.coverage:
        print(f"{GREEN}Coverage report generated.{RESET}")
        print(f"{GREEN}HTML report is available in htmlcov/index.html{RESET}")

    return success


def main():
    """Parse arguments and run requested checks."""
    parser = argparse.ArgumentParser(description="Run code quality checks and tests")
    parser.add_argument("--format", action="store_true", help="Format code with black and isort")
    parser.add_argument("--lint", action="store_true", help="Run flake8 linting")
    parser.add_argument("--type-check", action="store_true", help="Run mypy type checking")
    parser.add_argument("--test", action="store_true", help="Run tests")
    parser.add_argument("--all", action="store_true", help="Run all checks and tests")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("test_path", nargs="*", help="Specific test files or directories to test")

    args = parser.parse_args()

    # If no specific action is specified, run all checks
    if not any([args.format, args.lint, args.type_check, args.test, args.all]):
        args.all = True

    results = []

    # Run formatting if requested
    if args.format or args.all:
        results.append(("Formatting", format_code()))

    # Run linting if requested
    if args.lint or args.all:
        results.append(("Linting", run_linting()))

    # Run type checking if requested
    if args.type_check or args.all:
        results.append(("Type checking", run_type_checking()))

    # Run tests if requested
    if args.test or args.all:
        results.append(("Tests", run_tests(args)))

    # Print summary
    print("\n" + "=" * 50)
    print(f"{CYAN}SUMMARY:{RESET}")

    all_passed = True
    for name, success in results:
        status = f"{GREEN}PASSED{RESET}" if success else f"{RED}FAILED{RESET}"
        print(f"{name}: {status}")
        all_passed = all_passed and success

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
