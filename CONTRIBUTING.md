# Contributing to Festivo AI

Thank you for your interest in contributing to Festivo AI! 

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/festivo-ai.git`
3. Create a new branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Run tests and linting
6. Commit your changes: `git commit -m "Add your feature"`
7. Push to your branch: `git push origin feature/your-feature-name`
8. Open a Pull Request

## Development Setup

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### Frontend
```bash
cd frontend
npm ci
npm run dev
```

## Code Standards

- Follow existing code style and conventions
- Write tests for new features
- Run linting before submitting: `ruff check` (backend), `npm run lint` (frontend)
- Ensure type checking passes

## Pull Request Guidelines

- Provide a clear description of the changes
- Include tests for new functionality
- Update documentation as needed
- Ensure all tests pass
- Keep changes focused and atomic

## Questions?

Feel free to open an issue for questions or concerns.
