from datetime import datetime, timedelta
from pprint import pprint

import pytest

from . import github_api


@pytest.mark.asyncio
async def test_github_api_gets_user_right():
    # Only works if you have a valid GH_TOKEN set
    api = github_api.GithubAPI(owner="peterstolz")
    try:
        await api.get_versions("test")
    except AssertionError:
        pass
    assert api.is_user is True


@pytest.mark.asyncio
async def test_github_api_gets_packages():
    # Only works if you have a valid GH_TOKEN set
    api = github_api.GithubAPI(owner="prezero")
    res = await api.get_versions("hermes-backend")
    pprint(res)


def test_is_cut_off_date():
    image = github_api.Image(
        id=1, name="test", created_at=datetime.now(), updated_at=datetime.now()
    )
    # we create a delta of 1 day and an image that is 2 days old
    assert not image.is_before_cut_off_date(datetime.now() - timedelta(days=1))
    old_image_but_updated = github_api.Image(
        id=1,
        name="test",
        created_at=datetime.now() - timedelta(days=30),
        updated_at=datetime.now(),
    )
    assert not old_image_but_updated.is_before_cut_off_date(
        datetime.now() - timedelta(days=1)
    )
    assert old_image_but_updated.is_before_cut_off_date(
        datetime.now() - timedelta(days=1),
        use_updated=False,
    )
