# Django Working Groups Agent (Unofficial)

An AI Agent that generates and updates Django Software Foundation Working Group charters based on existing teams and templates.

**Please note:** This is not official or legal advice.

## Usage

```shell
# Ask about working groups or draft a charter
just ask "Please write a draft working group charter for the Accessibility team."

# Or use uv directly
uv run src/agent.py ask "Please write a draft working group charter for the Accessibility team."
```

## Available Commands

| Command | Description |
|---------|-------------|
| `just` | List all available commands |
| `just ask "..."` | Ask the working groups agent a question |
| `just debug` | Print the compiled system prompt for debugging |
| `just demo` | Run a demo with a sample question |
| `just bootstrap` | Install pip and uv |
| `just fmt` | Format code |
| `just lint` | Run pre-commit hooks on all files |
| `just lint-autoupdate` | Update pre-commit hooks to latest versions |

## Requirements

- Python 3.12+
- OpenAI API key (set `OPENAI_API_KEY` environment variable)

## Installation

```shell
just bootstrap
```
