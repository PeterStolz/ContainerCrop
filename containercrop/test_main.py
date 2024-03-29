from datetime import datetime, timedelta

from .github_api import Image
from .main import RetentionArgs, apply_retention_policy


def test_pydantic_parsing_happy_path():
    inp = {
        "image_names": "test",
        "cut_off": "1 day ago UTC",
        "token": "test",
        "untagged_only": "false",
        "skip_tags": "test",
        "keep_at_least": "0",
        "filter_tags": "test",
        "dry_run": "false",
        "repo_owner": "test",
    }
    args = RetentionArgs(**inp)
    assert args.image_names == "test"
    assert args.keep_at_least == 0


def test_apply_retention_policy_keep_at_least():
    policy = RetentionArgs(
        image_names="test",
        cut_off="1 day ago UTC",
        skip_tags="",
        keep_at_least=10,
        repo_owner="test",
    )
    # create 30 old images and verify that we keep 10
    images = [
        Image(
            id=i,
            name="test",
            created_at=datetime.now() - timedelta(days=30),
            updated_at=datetime.now() - timedelta(days=30),
        )
        for i in range(30)
    ]

    assert len(apply_retention_policy(policy, images)) == 10

    images = images[:5]
    assert len(apply_retention_policy(policy, images)) == 5
