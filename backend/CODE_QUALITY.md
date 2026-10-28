# Code Quality Guidelines

This document outlines code quality standards and practices for the Festivo AI backend.

## Tools

We use the following tools to maintain code quality:

- **[Ruff](https://docs.astral.sh/ruff/)** - Fast Python linter and formatter
- **[mypy](https://mypy.readthedocs.io/)** - Static type checker
- **[pytest](https://docs.pytest.org/)** - Testing framework with coverage

## Local Development

### Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### Running Checks

```bash
# Lint
ruff check app tests scripts

# Format
ruff format app tests scripts

# Type check
mypy app

# Tests with coverage
pytest
```

### Pre-commit Hook

Consider installing pre-commit hooks for automatic checks:

```bash
pip install pre-commit
pre-commit install
```

## Code Standards

### Type Hints
- All functions must have type hints for parameters and return values
- Use `typing` module types appropriately
- Avoid `Any` unless absolutely necessary

### Imports
- Imports are automatically sorted by Ruff (isort rules)
- Use absolute imports from `app.` package
- Group imports: standard library, third-party, local

### Style
- Line length: 100 characters
- Use double quotes for strings
- Follow PEP 8 conventions (enforced by Ruff)
- Use f-strings for string formatting

### Security
- Bandit rules are enforced (S prefix) - see exceptions in pyproject.toml
- Never log sensitive data (passwords, tokens, keys)
- Validate all inputs with Pydantic schemas

### Testing
- Minimum coverage: 70% (enforced in CI)
- Tests go in `tests/` directory
- Use fixtures from `conftest.py`
- Mark slow/integration tests appropriately

## Best Practices

1. **Single Responsibility**: Each function/class should do one thing well
2. **DRY**: Don't Repeat Yourself - extract common logic
3. **Error Handling**: Use custom exceptions from `app.core.exceptions`
4. **Logging**: Use structured logging, avoid print statements
5. **Documentation**: Add docstrings to public functions and classes
6. **Dependencies**: Keep dependencies up to date and minimal
7. **Async/Await**: Use async where appropriate for I/O operations
8. **Validation**: Validate at boundaries (API schemas, service layer)

## Common Issues to Avoid

- Mutable default arguments
- Bare except clauses
- Global mutable state
- SQL string concatenation (use parameterized queries)
- Hardcoded secrets or configuration
