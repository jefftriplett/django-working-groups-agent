# Django Working Groups Agent - Development Guidelines

## Commands
- **Run the agent**: `uv run agent.py "Your question here"` or `just ask "Your question here"`
- **Demo**: `just demo`
- **Linting**: `just lint` or `uv tool run --with pre-commit-uv pre-commit run --all-files`
- **Formatting**: `just fmt`
- **Install dependencies**: `just bootstrap`

## Code Style
- **Python version**: 3.12+ (targeting 3.13)
- **Line length**: 120 characters (enforced by Ruff)
- **Linting**: Uses Ruff with E and F codes enabled, ignoring E501 and E741
- **Imports**: Group standard library imports first, then third-party packages, then local modules
- **Types**: Use type annotations with Pydantic models for structured data
- **Naming**: Use snake_case for variables/functions and PascalCase for classes
- **Error handling**: Use explicit exception handling with appropriate error messages
- **Environment variables**: Use environs for managing environment variables
- **Output formatting**: Use Rich for terminal output formatting

## Project Structure
- Agent logic is contained in `agent.py`
- Cached content is stored in the `cache/` directory
- Configuration is managed via environment variables and defaults are provided