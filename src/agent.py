#!/usr/bin/env -S uv --quiet run
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "httpx2",
#     "environs",
#     "pydantic-ai-slim[openai,web]>=2,<3",
#     "rich",
#     "typer",
#     "uvicorn",
# ]
# ///

import subprocess
import time

import httpx2
import typer
import uvicorn

from environs import env
from pathlib import Path
from pydantic import BaseModel
from pydantic import Field
from pydantic_ai import Agent
from rich.console import Console

MEMORY_FILE = Path(__file__).parent.parent / "MEMORY.md"

DEFAULT_MEMORY_CONTENT = """\
# Memory

Additional context for the Django Working Groups agent.

## Examples of what to add here:

- Known board members and their roles
- Your role in the DSF (if applicable)
- Preferred charter formatting style
- Common terminology or naming conventions
- Notes about specific working groups
"""


def load_memory_from_markdown(filepath: Path = MEMORY_FILE) -> str | None:
    """Load memory markdown content. Returns None if file doesn't exist."""
    if not filepath.exists():
        return None
    return filepath.read_text()


def create_default_memory_file(filepath: Path = MEMORY_FILE) -> None:
    """Create a default MEMORY.md file."""
    filepath.write_text(DEFAULT_MEMORY_CONTENT)


def get_memory_context() -> str:
    """Generate memory context for the system prompt."""
    content = load_memory_from_markdown()
    if content is None:
        create_default_memory_file()
        return ""
    if content.strip() == DEFAULT_MEMORY_CONTENT.strip():
        return ""
    if not content.strip():
        return ""
    return f"<memory>\n\n{content}\n\n</memory>"


console = Console()

OPENAI_API_KEY: str = env.str("OPENAI_API_KEY")
OPENAI_MODEL_NAME: str = env.str("OPENAI_MODEL_NAME", default="openai:gpt-5.4-nano")

CACHE_MAX_AGE_HOURS: float = env.float("CACHE_MAX_AGE_HOURS", default=24.0)

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
    """Clone or pull the dsf-working-groups repository.

    Syncing is best effort. Generated charters sitting in the cache as untracked files
    will block a merge, and that should not stop the agent from running.
    """
    if (DSF_WORKING_GROUPS_DIR / ".git").exists():
        try:
            subprocess.run(
                ["git", "-C", str(DSF_WORKING_GROUPS_DIR), "pull", "--quiet"],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as error:
            console.print(f"[yellow]Could not update the charters, using the local copy: {error}[/yellow]")
    elif DSF_WORKING_GROUPS_DIR.exists():
        console.print(f"[yellow]{DSF_WORKING_GROUPS_DIR} is not a git clone — using the files as they are.[/yellow]")
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


def cache_is_fresh(filename: Path, max_age_hours: float) -> bool:
    """Return True if the cache file exists and is younger than max_age_hours."""
    if not filename.exists() or max_age_hours <= 0:
        return False

    return (time.time() - filename.stat().st_mtime) < (max_age_hours * 3600)


def fetch_and_cache(
    *,
    url: str,
    cache_file: str,
    timeout: float = 10.0,
    max_age_hours: float = CACHE_MAX_AGE_HOURS,
    refresh: bool = False,
):
    """Fetch content from URL and cache it locally."""
    filename = Path(OUTPUT_DIR, cache_file)
    if not refresh and cache_is_fresh(filename, max_age_hours):
        return filename.read_text()

    try:
        response = httpx2.get(f"https://r.jina.ai/{url}", timeout=timeout, follow_redirects=True)
        response.raise_for_status()
    except httpx2.HTTPError as exc:
        if filename.exists():
            console.print(f"[yellow]Could not refresh {filename}: {exc}. Using the cached copy.[/yellow]")
            return filename.read_text()
        raise

    contents = response.text

    filename.write_text(contents)

    return contents


def load_data(*, refresh: bool = False):
    # Sync the git repository (clone or pull)
    sync_git_repo()

    # Fetch foundation teams from Django website (not in git repo)
    foundation_teams = fetch_and_cache(
        url="https://www.djangoproject.com/foundation/teams/",
        cache_file="django-foundation-teams.md",
        refresh=refresh,
    )

    # Read files from local git checkout
    readme = read_repo_file("README.md")
    template = read_repo_file("template.md")

    # Get all active working groups dynamically
    working_groups = get_active_working_groups()

    # Format active working groups for the system prompt
    active_working_groups_text = ""
    for name, content in sorted(working_groups.items()):
        active_working_groups_text += f"## {name}\n\n{content}\n\n"

    memory = get_memory_context()

    return {
        "readme": readme,
        "foundation_teams": foundation_teams,
        "template": template,
        "active_working_groups": active_working_groups_text,
        "memory": memory,
    }


def get_agent(*, output_type=Output, refresh: bool = False):
    data = load_data(refresh=refresh)

    agent = Agent(
        model=OPENAI_MODEL_NAME,
        output_type=output_type,
        system_prompt=SYSTEM_PROMPT,
    )

    @agent.instructions
    def add_readme() -> str:
        return f"<readme>\n\n{data['readme']}\n\n</readme>"

    @agent.instructions
    def add_foundation_teams() -> str:
        return f"<foundation_teams>\n\n{data['foundation_teams']}\n\n</foundation_teams>"

    @agent.instructions
    def add_working_group_template() -> str:
        return f"<working_group_template>\n\n{data['template']}\n\n</working_group_template>"

    @agent.instructions
    def add_active_working_groups() -> str:
        return f"<active_working_groups>\n\n{data['active_working_groups']}\n\n</active_working_groups>"

    @agent.instructions
    def add_memory_context() -> str:
        return data["memory"]

    return agent


app = typer.Typer(
    help="Django Working Groups Agent - Help write working group charters",
    no_args_is_help=True,
)


@app.command()
def ask(
    question: str,
    refresh: bool = typer.Option(False, help="Re-fetch the source documents, ignoring the cache."),
):
    """Ask the working groups agent a question."""
    agent = get_agent(refresh=refresh)

    result = agent.run_sync(question)

    console.print(f"[yellow][bold]Reasoning:[/bold][/yellow] {result.output.reasoning}\n")
    console.print(f"[yellow][bold]Chair:[/bold][/yellow] {result.output.chair}\n")
    console.print(f"[yellow][bold]Co-Chair:[/bold][/yellow] {result.output.co_chair}\n")
    console.print(f"[yellow][bold]Board Liaison:[/bold][/yellow] {result.output.board_liaison}\n")

    if result.output.members:
        console.print("[yellow][bold]Members:[/bold][/yellow]")
        for member in result.output.members:
            console.print(f"- {member}")

    if result.output.sections:
        console.print("[yellow][bold]Sections:[/bold][/yellow]")
        for section in result.output.sections:
            console.print(f"- {section}")

    console.print(f"[green][bold]Charter:[/bold][/green] {result.output.charter}\n")


@app.command()
def web(
    host: str = "127.0.0.1",
    port: int = 8080,
    refresh: bool = typer.Option(False, help="Re-fetch the source documents, ignoring the cache."),
):
    """Launch the working groups agent as a web chat interface."""
    # output_type=str keeps replies conversational. Pydantic AI v2 rejects None here —
    # it reads it as "no output types provided" and raises UserError.
    agent = get_agent(output_type=str, refresh=refresh)
    web_app = agent.to_web()

    console.print(f"[bold green]Starting web interface at http://{host}:{port}[/bold green]")
    uvicorn.run(web_app, host=host, port=port)


@app.command()
def debug(
    refresh: bool = typer.Option(False, help="Re-fetch the source documents, ignoring the cache."),
):
    """Print the compiled system prompt for debugging."""
    data = load_data(refresh=refresh)

    console.print("[bold cyan]===== SYSTEM PROMPT =====[/bold cyan]\n")
    console.print(SYSTEM_PROMPT)
    console.print("\n[bold cyan]===== INSTRUCTIONS =====[/bold cyan]\n")
    console.print(f"<readme>\n\n{data['readme']}\n\n</readme>")
    console.print(f"\n<foundation_teams>\n\n{data['foundation_teams']}\n\n</foundation_teams>")
    console.print(f"\n<working_group_template>\n\n{data['template']}\n\n</working_group_template>")
    console.print(f"\n<active_working_groups>\n\n{data['active_working_groups']}\n\n</active_working_groups>")
    console.print("\n[bold cyan]===== MEMORY CONTEXT =====[/bold cyan]\n")
    if data["memory"]:
        console.print(data["memory"])
    else:
        console.print("[dim](no memory context)[/dim]")
    console.print("\n[bold cyan]=========================[/bold cyan]")


if __name__ == "__main__":
    app()
