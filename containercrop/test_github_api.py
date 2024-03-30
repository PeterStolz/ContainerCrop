from datetime import datetime, timedelta
from pprint import pprint

import pytest

from containercrop import github_api


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


def test_get_next_page_returns_link():
    link = '<https://api.github.com/organizations/1111/packages/container/backend/versions?page=2&per_page=30>; rel="next", <https://api.github.com/organizations/1111/packages/container/backend/versions?page=2&per_page=30>; rel="last"'
    assert (
        github_api.get_next_page(link)
        == "https://api.github.com/organizations/1111/packages/container/backend/versions?page=2&per_page=30"
    )


def test_various_link_header_formats():
    tests = [
        (
            {
                "link": '<https://api.github.com/organizations/1111/packages/container/backend/versions?page=2&per_page=30>; rel="next"',
                "expected": "https://api.github.com/organizations/1111/packages/container/backend/versions?page=2&per_page=30",
            }
        ),
        (
            {
                "link": '<https://api.github.com/organizations/1111/packages/container/backend/versions?page=2&per_page=30>; rel="last", <https://api.github.com/organizations/1111/packages/container/backend/versions?page=1&per_page=30>; rel="next"',
                "expected": "https://api.github.com/organizations/1111/packages/container/backend/versions?page=1&per_page=30",
            }
        ),
        (
            {
                "link": '<https://api.github.com/organizations/1111/packages/container/backend/versions?page=3&per_page=30>; rel="previous", <https://api.github.com/organizations/1111/packages/container/backend/versions?page=2&per_page=30>; rel="first", <https://api.github.com/organizations/1111/packages/container/backend/versions?page=4&per_page=30>; rel="next"',
                "expected": "https://api.github.com/organizations/1111/packages/container/backend/versions?page=4&per_page=30",
            }
        ),
        ({"link": "", "expected": None}),
        (
            {
                "link": '<https://api.github.com/organizations/1111/packages/container/backend/versions?page=2&per_page=30>; rel="first"',
                "expected": None,
            }
        ),
    ]

    for test in tests:
        assert (
            github_api.get_next_page(test["link"]) == test["expected"]
        ), f"Failed for link: {test['link']}"
