# Contributing to INEV SDK

Thank you for your interest in contributing to the INEV Python SDK!

## Development Setup

1. Clone the repository:
```bash
git clone https://github.com/Daily-Nerd/inev-sdk.git
cd inev-sdk
```

2. Install dependencies using uv:
```bash
pip install uv
uv pip install -e ".[dev]"
```

3. Run tests:
```bash
uv run pytest tests/ -v
```

## Code Style

- Follow PEP 8 guidelines
- Use type hints for all function signatures
- Write docstrings for public APIs
- Keep functions focused and testable

## Testing

- Add tests for all new features
- Ensure existing tests pass
- Aim for high test coverage
- Use pytest for test framework

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and ensure they pass
5. Commit your changes with a descriptive message
6. Push to your fork
7. Open a Pull Request

## Reporting Issues

- Use GitHub Issues to report bugs
- Include Python version, SDK version, and full traceback
- Provide minimal reproducible example if possible

## Questions?

Open a discussion on GitHub
