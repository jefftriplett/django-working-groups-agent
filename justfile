set dotenv-load := false

export JUST_UNSTABLE := "true"

# List all available commands
@_default:
    just --list

# Ask the working groups agent a question
@ask *ARGS:
    uv --quiet run src/agent.py ask "{{ ARGS }}"

# Print the compiled system prompt for debugging
@debug:
    uv --quiet run src/agent.py debug

# Install pip and uv package management tools
@bootstrap *ARGS:
    pip install --upgrade pip uv

# Run a demo with a sample question
@demo:
    just ask "Please write example charters for each of our existing Teams."

@demo_2:
    just ask "Please write a draft working grouop charter from the Accessibility team."

# Format code using just's built-in formatter
@fmt:
    just --fmt

# Run pre-commit hooks on all files
@lint *ARGS:
    uv --quiet tool run prek {{ ARGS }} --all-files

# Update pre-commit hooks to latest versions
@lint-autoupdate:
    uv --quiet tool run prek autoupdate
