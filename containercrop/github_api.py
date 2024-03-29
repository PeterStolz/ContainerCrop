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
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    tags: list[str] = Field(default_factory=list)

    @classmethod
    def from_github_entry(cls, entry: dict) -> "Image":
        return cls(
            id=entry["id"],
            name=entry["name"],
            url=entry.get("url"),
            updated_at=datetime.fromisoformat(entry["updated_at"]),
            created_at=datetime.fromisoformat(entry["created_at"]),
            tags=entry.get("metadata", {}).get("container", {}).get("tags"),
        )

    def is_before_cut_off_date(self, cut_off: datetime, use_updated=True) -> bool:
        time = self.updated_at if use_updated else self.created_at
        return time < cut_off


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
            headers={"Authorization": f"token {token}"},
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
                ), f"Unable to get user info for {self.owner}. Is the token valid"
                self.is_user = (await resp.json())["type"] == "User"
                logging.info("Owner is a user: %s", self.is_user)
        return self.is_user

    @ensure_user_checked
    async def _get_all_versions(self, url: str) -> list[Image]:
        "Get all versions of an image"
        # TODO get all pages and not just one
        async with self.session.get(url) as resp:
            assert resp.status == 200, f"Unable to get versions for {url}"
            return [Image.from_github_entry(elem) for elem in await resp.json()]

    @ensure_user_checked
    async def get_versions_for_user(self, image_name: str) -> list[Image]:
        "Get all versions of an image for a repo"
        assert self.is_user
        return await self._get_all_versions(
            f"{self.api_url}/user/packages/container/{image_name}/versions"
        )

    @ensure_user_checked
    async def get_versions_for_org(self, image_name: str) -> list[Image]:
        "Get all versions of an image for an org"
        assert not self.is_user
        return await self._get_all_versions(
            f"{self.api_url}/orgs/{self.owner}/packages/container/{image_name}/versions"
        )

    @ensure_user_checked
    async def get_versions(self, image_name: str) -> list[Image]:
        "Get all versions of an image"
        if self.is_user:
            return await self.get_versions_for_user(image_name)
        return await self.get_versions_for_org(image_name)

    async def delete_image(self, image: Image) -> bool:
        "Delete an image"
        return False

    async def delete_images(self, images: list[Image]) -> list[Image]:
        "Delete all images"
        return []
