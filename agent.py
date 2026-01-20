#!/usr/bin/env -S uv --quiet run
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "httpx",
#     "environs",
#     "pydantic-ai-slim[openai]",
#     "rich",
#     "typer",
# ]
# ///

import subprocess

import httpx
import typer

from environs import env
from pathlib import Path
from pydantic import BaseModel
from pydantic import Field
from pydantic_ai import Agent
from rich import print


OPENAI_API_KEY: str = env.str("OPENAI_API_KEY")
OPENAI_MODEL_NAME: str = env.str("OPENAI_MODEL_NAME", default="gpt-5-mini")

# Directory for saving results
OUTPUT_DIR: Path = Path(env.str("OUTPUT_DIR", default="cache"))
OUTPUT_DIR.mkdir(exist_ok=True)

# Git repository settings
DSF_WORKING_GROUPS_REPO = "https://github.com/django/dsf-working-groups.git"
DSF_WORKING_GROUPS_DIR: Path = OUTPUT_DIR / "dsf-working-groups"

SYSTEM_PROMPT = """
<system_context>

You are a Django Software Foundation expert on writing Django Working Groups and Teams charters.

</system_context>

<behavior_guidelines>

- Please read our readme for general questions and our working_group_template for our requirements.
- Using our foundation_teams for Teams that we would like to turn into workgroups.
- If you do not know who the chair, co-chair, or boar liason is, default to "TBD" instead of guessing.

</behavior_guidelines>
"""


class Output(BaseModel):
    charter: str = Field(..., description="Our draft or updated charter")

    chair: str | None = Field("TBD", description="The Chair of the working group")
    co_chair: str | None = Field("TBD", description="The Co-Chair of the working group")
    board_liaison: str | None = Field("TBD", description="The Board Liaison of the working group")
    members: list[str] | None = Field(None, description="The members of the working group")

    reasoning: str = Field(..., description="The reasoning and support for our answer based on our source material")
    sections: list[str] = Field(..., description="Sections to reference")


def sync_git_repo():
    """Clone or pull the dsf-working-groups repository."""
    if DSF_WORKING_GROUPS_DIR.exists():
        subprocess.run(
            ["git", "-C", str(DSF_WORKING_GROUPS_DIR), "pull", "--quiet"],
            check=True,
            capture_output=True,
        )
    else:
        subprocess.run(
            ["git", "clone", "--quiet", DSF_WORKING_GROUPS_REPO, str(DSF_WORKING_GROUPS_DIR)],
            check=True,
            capture_output=True,
        )


def read_repo_file(relative_path: str) -> str:
    """Read a file from the local dsf-working-groups checkout."""
    file_path = DSF_WORKING_GROUPS_DIR / relative_path
    return file_path.read_text()


def get_active_working_groups() -> dict[str, str]:
    """Read all active working group charters from the repository."""
    active_dir = DSF_WORKING_GROUPS_DIR / "active"
    working_groups = {}
    if active_dir.exists():
        for file_path in active_dir.glob("*.md"):
            name = file_path.stem
            working_groups[name] = file_path.read_text()
    return working_groups


def fetch_and_cache(
    *,
    url: str,
    cache_file: str,
    timeout: float = 10.0,
):
    """Fetch content from URL and cache it locally."""
    filename = Path(OUTPUT_DIR, cache_file)
    if filename.exists():
        return filename.read_text()

    response = httpx.get(f"https://r.jina.ai/{url}", timeout=timeout)
    response.raise_for_status()

    contents = response.text

    filename.write_text(contents)

    return contents


def get_agent():
    # Sync the git repository (clone or pull)
    sync_git_repo()

    # Fetch foundation teams from Django website (not in git repo)
    foundation_teams = fetch_and_cache(
        url="https://www.djangoproject.com/foundation/teams/",
        cache_file="django-foundation-teams.md",
    )

    # Read files from local git checkout
    readme = read_repo_file("README.md")
    working_group_template = read_repo_file("template.md")

    # Get all active working groups dynamically
    working_groups = get_active_working_groups()

    # Format active working groups for the system prompt
    active_working_groups_text = ""
    for name, content in sorted(working_groups.items()):
        active_working_groups_text += f"## {name}\n\n{content}\n\n"

    agent = Agent(
        model=OPENAI_MODEL_NAME,
        output_type=Output,
        system_prompt=SYSTEM_PROMPT,
    )

    @agent.instructions
    def add_readme() -> str:
        return f"<readme>\n\n{readme}\n\n</readme>"

    @agent.instructions
    def add_foundation_teams() -> str:
        return f"<foundation_teams>\n\n{foundation_teams}\n\n</foundation_teams>"

    @agent.instructions
    def add_working_group_template() -> str:
        return f"<working_group_template>\n\n{working_group_template}\n\n</working_group_template>"

    @agent.instructions
    def add_active_working_groups() -> str:
        return f"<active_working_groups>\n\n{active_working_groups_text}\n\n</active_working_groups>"

    return agent


def main(question: str, model_name: str = OPENAI_MODEL_NAME):
    agent = get_agent()

    result = agent.run_sync(question)

    print(f"[yellow][bold]Reasoning:[/bold][/yellow] {result.output.reasoning}\n")
    print(f"[yellow][bold]Chair:[/bold][/yellow] {result.output.chair}\n")
    print(f"[yellow][bold]Co-Chair:[/bold][/yellow] {result.output.co_chair}\n")
    print(f"[yellow][bold]Board Liaison:[/bold][/yellow] {result.output.board_liaison}\n")

    if result.output.members:
        print("[yellow][bold]Members:[/bold][/yellow]")
        for member in result.output.members:
            print(f"- {member}")

    if result.output.sections:
        print("[yellow][bold]Sections:[/bold][/yellow]")
        for section in result.output.sections:
            print(f"- {section}")

    print(f"[green][bold]Charter:[/bold][/green] {result.output.charter}\n")


if __name__ == "__main__":
    typer.run(main)
