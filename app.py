import json
from pathlib import Path
from shutil import copytree

from jinja2 import (
    Environment,
    FileSystemLoader,
    select_autoescape,
)

from github_service import GitHubService


# ==========================================
# CONFIGURATION
# ==========================================

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "docs"

GITHUB_USERNAME = "LauraMUD"
LANGUAGES = ("en", "es")


# ==========================================
# LOAD JSON
# ==========================================

def load_json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(
            f"Configuration file not found: {path}"
        )

    with path.open(encoding="utf-8") as file:
        return json.load(file)


# ==========================================
# LOAD PROFILE
# ==========================================

def load_profile() -> dict:
    profile = load_json(
        BASE_DIR / "data" / "profile.json"
    )

    profile["github_username"] = GITHUB_USERNAME
    profile["github_url"] = (
        f"https://github.com/{GITHUB_USERNAME}"
    )

    profile.setdefault("name", "Laura")
    profile.setdefault("professional_title", "Data Engineer")
    profile.setdefault("linkedin_url", "")
    profile.setdefault("email", "")
    profile.setdefault("skills", [])
    profile.setdefault("cv", {})

    # Validate CV files before displaying links.
    for language in LANGUAGES:
        cv_path = profile["cv"].get(language)

        if not cv_path:
            profile["cv"][language] = None
            continue

        relative_path = Path(cv_path)

        # CVs must be located inside static/.
        if (
            relative_path.is_absolute()
            or ".." in relative_path.parts
            or relative_path.parts[0] != "static"
        ):
            raise ValueError(
                f"Invalid CV path: {cv_path}"
            )

        full_path = BASE_DIR / relative_path

        if not full_path.is_file():
            print(
                f"WARNING: CV not found: {full_path}"
            )
            profile["cv"][language] = None

    return profile


# ==========================================
# PREPARE GITHUB PROJECTS
# ==========================================

def prepare_projects(
    repositories: list,
    config: dict,
) -> list:

    settings = config.get("settings", {})
    custom_projects = config.get("projects", {})

    excluded = {
        name.lower()
        for name in settings.get("excluded_repos", [])
    }

    projects = []

    for repo in repositories:
        name = repo["name"]

        if name.lower() in excluded:
            continue

        if (
            settings.get("exclude_forks", True)
            and repo.get("fork", False)
        ):
            continue

        if (
            settings.get("exclude_archived", True)
            and repo.get("archived", False)
        ):
            continue

        if (
            not settings.get(
                "show_all_public_repos", True
            )
            and name not in custom_projects
        ):
            continue

        custom = custom_projects.get(name, {})

        default_description = (
            repo.get("description")
            or "Explore this project on GitHub."
        )

        technologies = (
            custom.get("technologies")
            or [repo.get("language") or "Other"]
        )

        project = {
            "name": custom.get("title") or name,
            "description_en": (
                custom.get("description_en")
                or default_description
            ),
            "description_es": (
                custom.get("description_es")
                or default_description
            ),
            "technologies": technologies,
            "url": repo["html_url"],
            "featured": custom.get(
                "featured", False
            ),
            "priority": custom.get(
                "priority", 999
            ),
            "stars": repo.get(
                "stargazers_count", 0
            ),
            "updated_at": (
                repo.get("updated_at") or ""
            ),
        }

        projects.append(project)

    # Featured first, then priority,
    # then most recently updated.
    projects.sort(
        key=lambda p: p["updated_at"],
        reverse=True,
    )

    projects.sort(
        key=lambda p: (
            not p["featured"],
            p["priority"],
        )
    )

    max_projects = settings.get(
        "max_projects", 12
    )

    return projects[:max_projects]


# ==========================================
# BUILD PORTFOLIO
# ==========================================

def build_portfolio() -> None:

    print("Starting portfolio generation...")

    # Load configuration
    config = load_json(
        BASE_DIR / "data" / "projects.json"
    )

    profile = load_profile()

    # Fetch repositories from GitHub
    github = GitHubService(GITHUB_USERNAME)
    repositories = github.get_repositories()

    projects = prepare_projects(
        repositories,
        config,
    )

    print(
        f"GitHub repositories found: "
        f"{len(repositories)}"
    )

    print(
        f"Projects selected: {len(projects)}"
    )

    for project in projects:
        print(
            f" - {project['name']} "
            f"| featured={project['featured']}"
        )

    # Configure Jinja2
    env = Environment(
        loader=FileSystemLoader(
            BASE_DIR / "templates"
        ),
        autoescape=select_autoescape(
            ["html", "xml"]
        ),
    )

    template = env.get_template(
        "index.html"
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Generate both languages
    for language in LANGUAGES:

        translations = load_json(
            BASE_DIR
            / "data"
            / f"{language}.json"
        )

        other_language = (
            "es" if language == "en" else "en"
        )

        html = template.render(
            t=translations,
            lang=language,
            other_lang=other_language,
            name=profile["name"],
            profile=profile,
            github_username=GITHUB_USERNAME,
            projects=projects,
        )

        # Remove trailing whitespace from generated HTML
        html = "\n".join(
            line.rstrip(" \t")
            for line in html.split("\n")
        )

        destination = (
            OUTPUT_DIR / language
        )

        destination.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_file = (
            destination / "index.html"
        )

        output_file.write_text(
            html,
            encoding="utf-8",
        )

        print(
            f"Generated: {language}/index.html"
        )

    # Copy CSS and other static assets
    copytree(
        BASE_DIR / "static",
        OUTPUT_DIR / "static",
        dirs_exist_ok=True,
    )

    # Default landing page
    redirect_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport"
          content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="0;url=en/">
    <title>Laura | Data Engineer</title>
</head>
<body>
    <p>
        <a href="en/">Enter portfolio</a>
    </p>
</body>
</html>
"""

    (OUTPUT_DIR / "index.html").write_text(
        redirect_html,
        encoding="utf-8",
    )

    # Disable Jekyll processing
    (OUTPUT_DIR / ".nojekyll").touch()

    print(
        "Bilingual portfolio generated successfully!"
    )


# ==========================================
# ENTRY POINT
# ==========================================

if __name__ == "__main__":
    build_portfolio()
