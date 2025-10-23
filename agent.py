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

SYSTEM_PROMPT = """
<system_context>

You are a Django Software Foundation expert on writing Django Working Groups and Teams charters.

</system_context>

<behavior_guidelines>

- Please read our readme for general questions and our working_group_template for our requirements.
- Using our foundation_teams for Teams that we would like to turn into workgroups.
- If you do not know who the chair, co-chair, or boar liason is, default to "TBD" instead of guessing.

</behavior_guidelines>

<readme>

{readme}

</readme>

<foundation_teams>

{foundation_teams}

</foundation_teams>

<working_group_template>

{working_group_template}

</working_group_template>

"""


class Output(BaseModel):
    charter: str = Field(..., description="Our draft or updated charter")

    chair: str | None = Field("TBD", description="The Chair of the working group")
    co_chair: str | None = Field("TBD", description="The Co-Chair of the working group")
    board_liaison: str | None = Field("TBD", description="The Board Liaison of the working group")
    members: list[str] | None = Field(None, description="The members of the working group")

    reasoning: str = Field(..., description="The reasoning and support for our answer based on our source material")
    sections: list[str] = Field(..., description="Sections to reference")


def fetch_and_cache(
    *,
    url: str,
    cache_file: str,
    timeout: float = 10.0,
):
    filename = Path(OUTPUT_DIR, cache_file)
    if filename.exists():
        return filename.read_text()

    response = httpx.get(f"https://r.jina.ai/{url}", timeout=timeout)
    response.raise_for_status()

    contents = response.text

    filename.write_text(contents)

    return contents


def get_agent():
    foundation_teams = fetch_and_cache(
        url="https://www.djangoproject.com/foundation/teams/",
        cache_file="django-foundation-teams.md",
    )

    readme = fetch_and_cache(
        url="https://raw.githubusercontent.com/django/dsf-working-groups/refs/heads/main/README.md",
        cache_file="dsf-working-groups-readme.md",
    )

    working_group_template = fetch_and_cache(
        url="https://raw.githubusercontent.com/django/dsf-working-groups/refs/heads/main/template.md",
        cache_file="dsf-working-groups-template.md",
    )

    code_of_conduct = fetch_and_cache(
        url="https://raw.githubusercontent.com/django/dsf-working-groups/refs/heads/main/active/code-of-conduct.md",
        cache_file="working-groups-code-of-conduct.md",
    )
    # dceu = fetch_and_cache(
    #     url="https://raw.githubusercontent.com/django/dsf-working-groups/refs/heads/main/active/dceu.md",
    #     cache_file="working-groups-dceu.md",
    # )

    fellowship = fetch_and_cache(
        url="https://raw.githubusercontent.com/django/dsf-working-groups/refs/heads/main/active/fellowship.md",
        cache_file="working-groups-fellowship.md",
    )

    fundraising = fetch_and_cache(
        url="https://raw.githubusercontent.com/django/dsf-working-groups/refs/heads/main/active/fundraising.md",
        cache_file="working-groups-fundraising.md",
    )

    online_community = fetch_and_cache(
        url="https://raw.githubusercontent.com/django/dsf-working-groups/refs/heads/main/active/online-community.md",
        cache_file="working-groups-online-community.md",
    )

    social_media = fetch_and_cache(
        url="https://raw.githubusercontent.com/django/dsf-working-groups/refs/heads/main/active/social-media.md",
        cache_file="working-groups-social-media.md",
    )

    website = fetch_and_cache(
        url="https://raw.githubusercontent.com/django/dsf-working-groups/refs/heads/main/active/website.md",
        cache_file="working-groups-website.md",
    )

    system_prompt = SYSTEM_PROMPT.format(
        code_of_conduct=code_of_conduct,
        fellowship=fellowship,
        foundation_teams=foundation_teams,
        fundraising=fundraising,
        online_community=online_community,
        readme=readme,
        social_media=social_media,
        website=website,
        working_group_template=working_group_template,
    )

    agent = Agent(
        model=OPENAI_MODEL_NAME,
        output_type=Output,
        system_prompt=system_prompt,
    )

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
