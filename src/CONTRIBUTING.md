# Contributing to Research Hub Backend

Thank you for your interest in contributing!

## Getting Started
- Fork the repository and clone your fork.
- Create a virtual environment and install dependencies:
  ```
  python -m venv venv
  source venv/bin/activate  # On Windows: venv\Scripts\activate
  pip install -r requirements.txt
  ```
- Copy `.env.example` to `.env` and fill in your local values.
- Run the server with:
  ```
  uvicorn app.main:app --reload
  ```
- Run tests with:
  ```
  pytest
  ```

## Code Style
- Use [Black](https://black.readthedocs.io/en/stable/) for formatting.
- Use [isort](https://pycqa.github.io/isort/) for import sorting.
- Type annotations are required for all functions and methods.
- Write docstrings for all public functions, classes, and modules.

## Pull Requests
- Create a new branch for each feature or bugfix.
- Write clear, descriptive commit messages.
- Ensure all tests pass before submitting a PR.
- Reference related issues or feature requests in your PR description.
- PRs should be atomic and focused on a single change.

## Testing
- All new features must include tests.
- Use async tests with pytest and httpx.AsyncClient.
- Use a test database and Redis instance for integration tests.

## Communication
- Use GitHub Issues for bugs, feature requests, and questions.
- Be respectful and constructive in all discussions.

## Onboarding
- See the README for setup and architecture overview.
- Ask questions early and often—maintainers are happy to help! 