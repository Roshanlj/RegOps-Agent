#!/usr/bin/env python
"""
Simple test runner script for LLM provider tests

Usage:
    python run_tests.py
"""

import sys
import subprocess

def main():
    """Run pytest on the LLM provider tests"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/llm/test_providers.py", "-v"],
            capture_output=False,
            text=True
        )
        sys.exit(result.returncode)
    except Exception as e:
        print(f"Error running tests: {e}")
        print("\nMake sure pytest is installed:")
        print("  python -m pip install pytest pytest-mock")
        sys.exit(1)

if __name__ == "__main__":
    main()
