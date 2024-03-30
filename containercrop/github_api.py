import asyncio
import functools
import logging
import os
from datetime import datetime
from typing import Annotated

import aiohttp
from pydantic import BaseModel, Field


class Image(BaseModel):
    "API model response for an image"
    id: Annotated[int, Field(strict=True, ge=0)] = 1
    name: str = "dummyimage"
    url: str | None = None
    html_url: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    tags: list[str] = Field(default_factory=list)

    @classmethod
    def from_github_entry(cls, entry: dict) -> "Image":
        return cls(
            id=entry["id"],
            name=entry["name"],
            url=entry.get("url"),
            html_url=entry.get("html_url"),
            updated_at=datetime.fromisoformat(entry["updated_at"]),
            created_at=datetime.fromisoformat(entry["created_at"]),
            tags=entry.get("metadata", {}).get("container", {}).get("tags"),
        )

    def is_before_cut_off_date(self, cut_off: datetime, use_updated=True) -> bool:
        time = self.updated_at if use_updated else self.created_at
        return time < cut_off

    def __str__(self) -> str:
        return f"Image {self.name}({self.html_url}) updated at {self.updated_at} with tags {self.tags}"


def get_next_page(link_header: str | None) -> str | None:
    """Parse GitHub's link header and return the next URL."""
    if not link_header:
        return None

    links = link_header.split(",")
    for link in links:
        parts = link.split(";")
        if len(parts) == 2 and parts[1].strip() == 'rel="next"':
            next_link = parts[0].strip("<> ")
            return next_link

    return None


class GithubAPI:
    "Interact with images"

    def __init__(
        self,
        owner: str,
        token: str | None = None,
        api_url: str = "https://api.github.com",
        is_user: bool | None = None,
    ):
        token = token or os.environ.get("GH_TOKEN")
        if not token:
            raise ValueError("Token is required")
        self.token: str = token
        self.owner: str = owner
        self.api_url: str = api_url
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"token {token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=aiohttp.ClientTimeout(total=5),
        )
        self.is_user: bool | None = is_user

    @staticmethod
    def ensure_user_checked(method):
        """
        A decorator within the class to ensure check_is_user is called
        before the method. This is needed because the API calls are different
        """

        @functools.wraps(method)
        async def wrapper(self, *args, **kwargs):
            await self.check_is_user()
            return await method(self, *args, **kwargs)

        return wrapper

    async def check_is_user(self):
        "Check if owner is org or user"
        if self.is_user is None:
            async with self.session.get(f"{self.api_url}/users/{self.owner}") as resp:
                assert (
                    resp.status == 200
                ), f"Unable to get user info for {self.owner}. Is the token valid?"
                self.is_user = (await resp.json())["type"] == "User"
                logging.info("Owner is a user: %s", self.is_user)
        return self.is_user

    @ensure_user_checked
    async def _get_all_versions(self, url: str) -> list[Image]:
        "Get all versions of an image"
        images: list[Image] = []
        next_url: str | None = url
        while next_url:
            async with self.session.get(next_url) as response:
                if response.status != 200:
                    logging.warning(
                        "Failed to fetch versions for %s. Status: %s, Response: %s",
                        url,
                        response.status,
                        await response.text(),
                    )
                    break

                data = await response.json()
                images.extend(Image.from_github_entry(elem) for elem in data)

                link_header = response.headers.get("Link")
                next_url = get_next_page(
                    link_header
                )  # Update URL to the next page or None if there's no next page
                if next_url:
                    logging.debug("Fetching next page: %s", next_url)

        return images

    @ensure_user_checked
    async def get_versions_for_user(self, image_name: str) -> list[Image]:
        "Get all versions of an image for a repo"
        assert self.is_user
        return await self._get_all_versions(
            f"{self.api_url}/user/packages/container/{image_name}/versions?per_page=100"
        )

    @ensure_user_checked
    async def get_versions_for_org(self, image_name: str) -> list[Image]:
        "Get all versions of an image for an org"
        assert not self.is_user
        return await self._get_all_versions(
            f"{self.api_url}/orgs/{self.owner}/packages/container/{image_name}/versions?per_page=100"
        )

    @ensure_user_checked
    async def get_versions(self, image_name: str) -> list[Image]:
        "Get all versions of an image"
        if self.is_user:
            return await self.get_versions_for_user(image_name)
        return await self.get_versions_for_org(image_name)

    @ensure_user_checked
    async def delete_image(self, image: Image) -> bool:
        "Delete an image"
        async with self.session.delete(image.url) as resp:
            if resp.status == 204:
                return True
            logging.error(
                "Unable to delete image %s(%s) with status %s",
                image.name,
                image.url,
                resp.status,
            )
        return False

    @ensure_user_checked
    async def delete_images(self, images: list[Image]) -> list[bool]:
        "Delete all images"
        # TODO This probably needs to be throttled
        return await asyncio.gather(*[self.delete_image(image) for image in images])
