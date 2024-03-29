"""
ContainerCrop - A tool to clean up your github container registry
and keep only the images you need.
"""

import os
from datetime import datetime
from typing import Annotated

from dateparser import parse
from pydantic import BaseModel, Field, field_validator

from .github_api import Image


def get_args_from_env() -> dict[str, str | None]:
    return {
        "image_names": os.environ.get("IMAGE_NAMES"),
        "cut_off": os.environ.get("CUT_OFF"),
        "token": os.environ.get("TOKEN"),
        "untagged_only": os.environ.get("UNTAGGED_ONLY"),
        "skip_tags": os.environ.get("SKIP_TAGS"),
        "keep_at_least": os.environ.get("KEEP_AT_LEAST"),
        "filter_tags": os.environ.get("FILTER_TAGS"),
        "dry_run": os.environ.get("DRY_RUN"),
        "repo_owner": os.environ.get("REPO_OWNER"),
    }


class RetentionArgs(BaseModel):
    "Parses and holds the args for the retention policy."
    image_names: str
    cut_off: datetime
    token: str | None = None
    untagged_only: bool = False
    skip_tags: list[str]
    keep_at_least: Annotated[int, Field(ge=0)]
    filter_tags: list[str] = Field(default_factory=list)
    dry_run: bool = False
    repo_owner: str

    @classmethod
    def from_env(cls) -> "RetentionArgs":
        return cls(**get_args_from_env())

    def __str__(self) -> str:
        return f"Args: {self.__dict__}"

    @field_validator("skip_tags", "filter_tags", mode="before")
    @classmethod
    def validate_tags(cls, v: str) -> list[str]:
        return cls.get_comma_splits(v)

    @staticmethod
    def get_comma_splits(inp: str) -> list[str]:
        return [sub.strip() for sub in inp.split(",")] if inp else []

    @field_validator("cut_off", mode="before")
    @classmethod
    def parse_human_readable_datetime(cls, v: str) -> datetime:
        parsed_cutoff = parse(v)
        if not parsed_cutoff:
            raise ValueError(f"Unable to parse '{v}'")
        elif (
            parsed_cutoff.tzinfo is None
            or parsed_cutoff.tzinfo.utcoffset(parsed_cutoff) is None
        ):
            raise ValueError("Timezone is required for the cut-off")
        return parsed_cutoff


def apply_retention_policy(args: RetentionArgs, images: list[Image]) -> list[Image]:
    """
    Apply the retention policy to the images and return the ones that should be deleted.
    """
    # to implement here: cut-off, untagged_only, skip_tags, keep_at_leat, filter_tags
    # cut-off

    return images[: args.keep_at_least]


async def main():
    args = RetentionArgs.from_env()
    print(args)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
