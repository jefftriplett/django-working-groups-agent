# Django Working Groups Agent (Unofficial)

An AI Agent that generates and updates Django Software Foundation Working Group charters based on existing teams and templates.

**Please note:** This is not official or legal advice.

## Requirements

- Python 3.12+ (targeting 3.13)
- [uv](https://github.com/astral-sh/uv) package manager

## Installation

```shell
# Install required tools
pip install --upgrade pip uv

# Install dependencies
just bootstrap
```

## Usage

```shell
# Using uv directly
$ uv run src/agent.py "Please write a draft working group charter for the Accessibility team."

# Using just command
$ just ask "Please write a draft working group charter for the Accessibility team."

# Quick demo with sample question
$ just demo
```

### Example Output

```
Reasoning: I've created a charter for the Django Accessibility Working Group based on the template provided and the information available about Django Foundation teams. This charter follows the standard format used by other working groups, defining the purpose, responsibilities, deliverables, and operational procedures for a dedicated accessibility-focused working group.

Chair: TBD

Co-Chair: TBD

Board Liaison: TBD

Sections:
- Working Group Template
- Foundation Teams

Charter: # Django Accessibility Working Group Charter

## Purpose

The Django Accessibility Working Group exists to improve and maintain accessibility standards across the Django project and its ecosystem. The group works to ensure that Django follows best practices for accessibility, making the framework and its resources usable by people of all abilities and disabilities.

## Responsibilities

- Develop and maintain accessibility guidelines for Django's codebase, documentation, and websites
- Review and improve accessibility of Django's web properties (djangoproject.com, docs, etc.)
- Provide guidance to the community on implementing accessible Django applications
- Collaborate with other working groups to ensure accessibility is considered in all Django initiatives
- Stay current with evolving accessibility standards (WCAG, ARIA, etc.) and recommend implementations
- Create educational resources about accessibility best practices for the Django community

...
```

## Development

This project uses:
- Rich for terminal output formatting
- Pydantic-AI for agent configuration
- Environment variables for configuration (OPENAI_API_KEY, OPENAI_MODEL_NAME)
- Content caching to reduce API calls
- Ruff for linting with a line length of 120 characters

## Available Commands

```shell
# List all available commands
$ just

# Ask the agent a question
$ just ask "Your question here"

# Run a demo with sample question
$ just demo

# Format code
$ just fmt

# Run linting
$ just lint

# Install dependencies
$ just bootstrap
```

## License

See the [LICENSE.md](LICENSE.md) file for details.
