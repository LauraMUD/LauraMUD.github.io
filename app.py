
import json
from datetime import datetime, timezone
from pathlib import Path
from shutil import copytree

from jinja2 import (
    Environment,
    FileSystemLoader,
    select_autoescape,
)

from github_service import GitHubService


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "docs"

GITHUB_USERNAME = "LauraMUD"
PORTFOLIO_NAME = "Laura"
LANGUAGES = ["en", "es"]

SKILLS = [
    "Python",
    "SQL",
    "PostgreSQL",
    "ETL / ELT",
    "Data Modeling",
    "Git & GitHub",
]


def load_json(path):
    with open(path, encoding="utf-8") as file:
        return json.load(file)


def prepare_projects(repositories, config):
    settings = config["settings"]
    custom_projects = config["projects"]

    excluded = {
        name.lower()
        for name in settings.get("excluded_repos", [])
    }

    projects = []

    for repo in repositories:
        name = repo["name"]

        if name.lower() in excluded:
            continue

        if settings.get("exclude_forks", True) and repo["fork"]:
            continue

        if settings.get("exclude_archived", True) and repo["archived"]:
            continue

        custom = custom_projects.get(name, {})

        # Optional allowlist mode.
        if not settings.get("show_all_public_repos", True):
            if name not in custom_projects:
                continue

        default_description = (
            repo.get("description")
            or "Explore this data engineering project."
        )

        project = {
            "name": custom.get("title", name),
            "description_en": custom.get(
                "description_en",
                default_description,
            ),
            "description_es": custom.get(
                "description_es",
                default_description,
            ),
            "technologies": custom.get(
                "technologies",
                [repo.get("language") or "Other"],
            ),
            "url": repo["html_url"],
            "featured": custom.get("featured", False),
            "priority": custom.get("priority", 999),
            "stars": repo.get("stargazers_count", 0),
            "updated_at": repo.get("updated_at") or "",
        }

        projects.append(project)

    projects.sort(
        key=lambda p: (
            not p["featured"],
            p["priority"],
            -p["stars"],
            p["name"].lower(),
        )
    )

    return projects[:settings.get("max_projects", 12)]


def build_portfolio():
    config = load_json(
        BASE_DIR / "data" / "projects.json"
    )

    github = GitHubService(GITHUB_USERNAME)
    repositories = github.get_repositories()

    projects = prepare_projects(repositories, config)

    print(f"GitHub repositories found: {len(repositories)}")
    print(f"Projects selected: {len(projects)}")

    for project in projects:
        print(
            f" - {project['name']}"
            f" | featured={project['featured']}"
        )

    env = Environment(
        loader=FileSystemLoader(BASE_DIR / "templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )

    template = env.get_template("index.html")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for language in LANGUAGES:
        translations = load_json(
            BASE_DIR / "data" / f"{language}.json"
        )

        other_language = (
            "es" if language == "en" else "en"
        )

        html = template.render(
            t=translations,
            lang=language,
            other_lang=other_language,
            name=PORTFOLIO_NAME,
            github_username=GITHUB_USERNAME,
            skills=SKILLS,
            projects=projects,
        )

        destination = OUTPUT_DIR / language
        destination.mkdir(parents=True, exist_ok=True)

        (destination / "index.html").write_text(
            html,
            encoding="utf-8",
        )

        print(f"Generated: {language}/index.html")

    copytree(
        BASE_DIR / "static",
        OUTPUT_DIR / "static",
        dirs_exist_ok=True,
    )

    (OUTPUT_DIR / "index.html").write_text(
        '<!DOCTYPE html><html lang="en"><head>'
        '<meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta http-equiv="refresh" content="0;url=en/">'
        '<title>Laura | Data Engineer</title>'
        '</head><body>'
        '<p><a href="en/">Enter portfolio</a></p>'
        '</body></html>',
        encoding="utf-8",
    )

    (OUTPUT_DIR / ".nojekyll").touch()

    print("Bilingual portfolio generated successfully!")


if __name__ == "__main__":
    build_portfolio()
