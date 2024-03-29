from datetime import datetime, timedelta, timezone

import pytest

from .github_api import Image
from .main import RetentionArgs, apply_retention_policy


@pytest.fixture
def generate_images():
    """Generate images with different properties."""

    def _generator(tags_list, days_old_list, names_list):
        return [
            Image(
                id=i,
                name=names_list[i % len(names_list)],
                created_at=datetime.now(timezone.utc)
                - timedelta(days=days_old_list[i % len(days_old_list)]),
                updated_at=datetime.now(timezone.utc)
                - timedelta(days=days_old_list[i % len(days_old_list)]),
                tags=tags_list[i % len(tags_list)],
            )
            for i in range(len(tags_list))
        ]

    return _generator


def test_RetentionArgs_parsing_happy_path():
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


def test_RetentionArgs_cant_set_both_skip_tags_and_untagged_only():
    inp = {
        "image_names": "test",
        "cut_off": "1 day ago UTC",
        "untagged_only": "true",
        "skip_tags": "test",
        "filter_tags": "test",
        "dry_run": "false",
        "repo_owner": "test",
    }
    with pytest.raises(ValueError):
        RetentionArgs(**inp)


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
            created_at=datetime.now(timezone.utc) - timedelta(days=30),
            updated_at=datetime.now(timezone.utc) - timedelta(days=30),
        )
        for i in range(30)
    ]

    assert len(apply_retention_policy(policy, images)) == 20

    images = images[:5]
    assert len(apply_retention_policy(policy, images)) == 0


def test_delete_untagged_images_older_than_one_day():
    policy = RetentionArgs(
        image_names="test",
        cut_off="1 day ago UTC",
        skip_tags="",
        keep_at_least=0,
        repo_owner="test",
        untagged_only=True,
    )
    # create 30 old images and verify that we keep 10
    images = [
        Image(
            id=i,
            name="test",
            created_at=datetime.now(timezone.utc) - timedelta(days=30),
            updated_at=datetime.now(timezone.utc) - timedelta(days=30),
            tags=[],
        )
        for i in range(30)
    ]

    assert len(apply_retention_policy(policy, images)) == 30

    images = images[:5]
    assert len(apply_retention_policy(policy, images)) == 5


def test_filter_by_specific_tags_for_deletion(generate_images):
    images = generate_images(
        tags_list=[["v1"], ["v1.0"], ["beta"], ["latest"]],
        days_old_list=[5, 5, 5, 5],
        names_list=["image1"],
    )
    policy = RetentionArgs(
        image_names="image1",
        cut_off="20 days ago UTC",
        untagged_only=False,
        skip_tags="",
        keep_at_least=0,
        filter_tags="v1,v1.0",
        dry_run=True,
        token="dummy_token",
        repo_owner="test",
    )
    assert len(apply_retention_policy(policy, images)) == 2


def test_skip_specific_tags(generate_images):
    images = generate_images(
        tags_list=[["v1"], ["beta"], ["latest"]],
        days_old_list=[1, 2, 3],
        names_list=["image1"],
    )
    policy = RetentionArgs(
        image_names="image1",
        cut_off="1 day ago UTC",
        untagged_only=False,
        skip_tags="beta,latest",
        keep_at_least=0,
        filter_tags="",
        dry_run=True,
        token="dummy_token",
        repo_owner="test",
    )
    assert (
        len(apply_retention_policy(policy, images)) == 1
    )  # Only "v1" is eligible for deletion


def test_keep_at_least_n_images(generate_images):
    images = generate_images(
        tags_list=[[], ["v1"], ["latest"]],
        days_old_list=[10, 15, 20],
        names_list=["image1"],
    )
    policy = RetentionArgs(
        image_names="image1",
        cut_off="5 days ago UTC",
        untagged_only=False,
        skip_tags="",
        keep_at_least=2,
        filter_tags="",
        repo_owner="test",
    )
    assert (
        len(apply_retention_policy(policy, images)) == 1
    )  # Despite all being old, 2 must be kept


def test_delete_untagged_images_older_than_x_days(generate_images):
    images = generate_images(
        tags_list=[[], [], [], ["v1"], ["latest"]],
        days_old_list=[3, 4, 5, 1, 2],
        names_list=["image1", "image2"],
    )
    policy = RetentionArgs(
        image_names="image1,image2",
        cut_off="2 days ago UTC",
        untagged_only=True,
        skip_tags="",
        keep_at_least=0,
        filter_tags="",
        repo_owner="test",
    )
    to_delete = apply_retention_policy(policy, images)
    assert len(to_delete) == 3
    assert all(
        img.tags == [] for img in to_delete
    )  # Ensure all deleted images are untagged


def test_delete_tagged_keep_recent_untagged(generate_images):
    images = generate_images(
        tags_list=[["v1"], [], ["v2"], []],
        days_old_list=[10, 1, 10, 2],
        names_list=["image1"],
    )
    policy = RetentionArgs(
        image_names="image1",
        cut_off="5 days ago UTC",
        untagged_only=False,
        skip_tags="",
        keep_at_least=0,
        filter_tags="",
        repo_owner="test",
    )
    deleted_images = apply_retention_policy(policy, images)
    assert len(deleted_images) == 2  # Should keep the 2 recent tagged images
    print(deleted_images)
    assert all(
        img.tags != [] for img in deleted_images
    )  # Ensure the kept images are untagged


@pytest.mark.skip
def test_dry_run_does_not_delete_images(generate_images):
    images = generate_images(
        tags_list=[["v1"], ["v2"]], days_old_list=[10, 20], names_list=["image1"]
    )
    initial_image_count = len(images)
    policy = RetentionArgs(
        image_names="image1",
        cut_off="5 days ago UTC",
        untagged_only=False,
        skip_tags="",
        keep_at_least=0,
        filter_tags="",
        dry_run=True,  # Important: This is a dry run
        token="dummy_token",
        repo_owner="test",
    )
    images = apply_retention_policy(policy, images)
    # Assuming apply_retention_policy modifies the list of images when not in dry run
    assert (
        len(images) == initial_image_count
    )  # Ensure no images are actually deleted in dry run


def test_keep_all_images_when_keep_at_least_equals_total(generate_images):
    images = generate_images(
        tags_list=[[], ["v1"]], days_old_list=[30, 30], names_list=["image1", "image2"]
    )
    policy = RetentionArgs(
        image_names="image1,image2",
        cut_off="1 day ago UTC",
        untagged_only=False,
        skip_tags="",
        keep_at_least=len(images),  # Set to keep all images
        filter_tags="",
        repo_owner="test",
    )
    assert (
        len(apply_retention_policy(policy, images)) == 0
    )  # Expect no images to be marked for deletion


def test_wildcard_tag_filtering(generate_images):
    images = generate_images(
        tags_list=[["v1.1"], ["v1.2"], ["beta"], ["latest"]],
        days_old_list=[10, 15, 5, 20],
        names_list=["image1"],
    )
    policy = RetentionArgs(
        image_names="image1",
        cut_off="3 days ago UTC",
        untagged_only=False,
        skip_tags="v1.*",  # Skip any version starting with v1.
        keep_at_least=0,
        filter_tags="*",  # Consider all tags
        repo_owner="test",
    )
    retained_images = apply_retention_policy(policy, images)
    assert (
        len(retained_images) == 2
    )  # "beta" and possibly "latest" if not matching skip_tags wildcard
    assert not any(
        "v1" in tag for img in retained_images for tag in img.tags
    )  # No v1.* tags
