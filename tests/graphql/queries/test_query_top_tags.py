"""Tests for the ``getTopTags`` query."""

import pytest

from tests.graphql.helpers import GET_TOP_TAGS, assert_no_errors


pytestmark = pytest.mark.query


async def test_get_top_tags_returns_sorted_desc(execute_gql, tag_factory):
    await tag_factory(name="rare", tag_count=1)
    await tag_factory(name="popular", tag_count=99)
    await tag_factory(name="medium", tag_count=10)

    result = await execute_gql(GET_TOP_TAGS)

    assert_no_errors(result)
    tags = result.data["getTopTags"]
    assert [t["name"] for t in tags] == ["popular", "medium", "rare"]
    assert [t["count"] for t in tags] == [99, 10, 1]


async def test_get_top_tags_respects_homepage_limit(
    execute_gql, tag_factory, test_settings
):
    limit = test_settings.page_size_default.homepage_tags
    for i in range(limit + 5):
        await tag_factory(name=f"tag-{i:03d}", tag_count=i)

    result = await execute_gql(GET_TOP_TAGS)

    assert_no_errors(result)
    assert len(result.data["getTopTags"]) == limit


async def test_get_top_tags_empty_db(execute_gql, init_db):
    result = await execute_gql(GET_TOP_TAGS)
    assert_no_errors(result)
    assert result.data["getTopTags"] == []


async def test_get_top_tags_no_categories_returns_empty(
    execute_gql, tag_factory, monkeypatch, test_settings
):
    await tag_factory(name="x", tag_count=10)
    monkeypatch.setattr(test_settings, "resource_paths", {})

    result = await execute_gql(GET_TOP_TAGS)

    assert_no_errors(result)
    assert result.data["getTopTags"] == []
