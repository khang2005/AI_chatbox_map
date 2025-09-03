# AGENTS.md

This file provides guidelines for agentic coding agents operating in this repository.

## Build/Lint/Test Commands

*   **Test:** `pytest` (runs all tests)
*   **Run a single test:**  `pytest <test_file_path> -k <test_name>` (e.g., `pytest test.py -k test_hello`)
*   **Lint:** `ruff check .`

## Code Style Guidelines

*   **Language:** Python
*   **Imports:** Follow standard Python import conventions.
*   **Formatting:** Adhere to PEP 8 style guidelines.
*   **Types:** Use type hints for function arguments and return values.
*   **Naming Conventions:** Use snake_case for variable and function names. Use PascalCase for class names.
*   **Error Handling:** Implement appropriate try-except blocks for error handling.
*   **File Structure:** Organize code into logical modules and packages.

## Rules

*   No specific rules found in `.cursor/rules/`, `.cursorrules`, or `.github/copilot-instructions.md`.
