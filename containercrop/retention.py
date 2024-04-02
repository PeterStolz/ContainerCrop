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

from containercrop.github_api import GithubAPI, Image


def get_args_from_env() -> dict[str, str | None]:
    return {
        "image_name": os.environ.get("IMAGE_NAME"),
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
    image_name: str
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
        return cls(**get_args_from_env())  # type: ignore

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
        logging.debug("Image %s(%s) does match skip tags", image.name, image.html_url)
        return False
    if args.untagged_only and image.tags:
        logging.debug(
            "Image %s(%s) is tagged and untagged_only is set",
            image.name,
            image.html_url,
        )
        return False
    if args.cut_off and image.is_before_cut_off_date(args.cut_off):
        logging.debug("Image %s(%s) is before cut-off date", image.name, image.html_url)
        return True
    if args.filter_tags and any(
        any(fnmatch(tag, filter_tag) for filter_tag in args.filter_tags)
        for tag in image.tags
    ):
        logging.debug("Image %s(%s) does match filter tags", image.name, image.html_url)
        return True
    logging.debug(
        "Image %s(%s) does not match any policy, therefore we keep it",
        image.name,
        image.html_url,
    )
    return False


def apply_retention_policy(args: RetentionArgs, images: list[Image]) -> list[Image]:
    """
    Apply the retention policy to the images and return the ones that should be deleted.
    """
    matches = [image for image in images if matches_retention_policy(image, args)]
    return matches[args.keep_at_least :]


async def main(retention_args: RetentionArgs):
    api = GithubAPI(owner=retention_args.repo_owner, token=retention_args.token)
    images = await api.get_versions(retention_args.image_name)
    to_delete = apply_retention_policy(retention_args, images)
    if not retention_args.dry_run:
        logging.info("Will delete %s images", len(to_delete))
        logging.info(
            "Images to delete: \n\t%s", "\n\t".join(str(img) for img in to_delete)
        )
        await api.delete_images(to_delete)
        logging.info(
            "If you deleted images you want to keep don't panic you have 30 days to recoer them. You can check out https://docs.github.com/en/packages/learn-github-packages/deleting-and-restoring-a-package#restoring-packages"
        )
    else:
        logging.info("Would delete %s images but dry_run is enabled", len(to_delete))
        logging.info(
            "Images that would be deleted: \n\t%s",
            "\n\t".join(str(img) for img in to_delete),
        )
    logging.info("Done")
