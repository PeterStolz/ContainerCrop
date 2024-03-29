"""
ContainerCrop - A tool to clean up your github container registry
and keep only the images you need.
"""

import logging
import os
from datetime import datetime
from fnmatch import fnmatch
from typing import Annotated

from dateparser import parse
from pydantic import BaseModel, Field, field_validator, model_validator

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
    keep_at_least: Annotated[int, Field(ge=0)] = 0
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

    @model_validator(mode="after")
    def check_skip_tags_and_untagged_only(self) -> "RetentionArgs":
        if self.untagged_only and self.skip_tags:
            raise ValueError("Cannot set both `untagged_only` and `skip_tags`.")
        return self


def matches_retention_policy(image: Image, args: RetentionArgs) -> bool:
    """
    Check if the image matches the retention policy.
    :param image: The image to check
    :param args: The retention policy
    :return: True if the image should be deleted
    """
    if args.skip_tags and any(
        any(fnmatch(tag, skip_tag) for skip_tag in args.skip_tags) for tag in image.tags
    ):
        logging.debug(f"Image {image.name} does match skip tags")
        return False
    if args.untagged_only and image.tags:
        logging.debug(f"Image {image.name} is tagged and untagged_only is set")
        return False
    if args.cut_off and image.is_before_cut_off_date(args.cut_off):
        logging.debug(f"Image {image.name} is before cut-off date")
        return True
    if args.filter_tags and any(
        any(fnmatch(tag, filter_tag) for filter_tag in args.filter_tags)
        for tag in image.tags
    ):
        logging.debug(f"Image {image.name} does match filter tags")
        return True
    logging.debug(f"Image {image.name} does not match any policy, therefore we keep it")
    return False


def apply_retention_policy(args: RetentionArgs, images: list[Image]) -> list[Image]:
    """
    Apply the retention policy to the images and return the ones that should be deleted.
    """
    matches = [image for image in images if matches_retention_policy(image, args)]
    return matches[args.keep_at_least :]


async def main():
    args = RetentionArgs.from_env()
    print(args)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
