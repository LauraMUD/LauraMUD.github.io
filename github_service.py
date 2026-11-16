
import os

import requests


class GitHubService:
    BASE_URL = "https://api.github.com"

    def __init__(self, username):
        self.username = username

        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github+json",
            "User-Agent": "data-engineer-portfolio",
        })

        token = os.getenv("GITHUB_TOKEN")

        if token:
            self.session.headers["Authorization"] = (
                f"Bearer {token}"
            )

    def get_repositories(self):
        url = (
            f"{self.BASE_URL}/users/"
            f"{self.username}/repos"
        )

        repositories = []
        page = 1

        while True:
            response = self.session.get(
                url,
                params={
                    "per_page": 100,
                    "page": page,
                    "sort": "updated",
                    "direction": "desc",
                    "type": "owner",
                },
                timeout=20,
            )

            response.raise_for_status()
            batch = response.json()

            if not isinstance(batch, list):
                raise ValueError(
                    "Unexpected GitHub API response"
                )

            repositories.extend(batch)

            if len(batch) < 100:
                break

            page += 1

        return repositories
