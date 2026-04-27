"""Tests for the ``getSuggestions`` query."""

import pytest

from tests.graphql.helpers import (
    GET_SUGGESTIONS,
    assert_error_contains,
    assert_no_errors,
)


pytestmark = pytest.mark.query


def _input(keyword: str | None, suggestion_type: str) -> dict:
    return {"keyword": {"keyWord": keyword}, "suggestionType": suggestion_type}


async def test_suggestions_empty_keyword_returns_empty(execute_gql, init_db):
    result = await execute_gql(
        GET_SUGGESTIONS, {"input": _input(None, "Tag")}
    )
    assert_no_errors(result)
    assert result.data["getSuggestions"] == []


async def test_suggestions_tag_prefix_match(execute_gql, tag_factory):
    await tag_factory(name="action", tag_count=10)
    await tag_factory(name="adventure", tag_count=5)
    await tag_factory(name="comedy", tag_count=20)

    result = await execute_gql(
        GET_SUGGESTIONS, {"input": _input("a", "Tag")}
    )

    assert_no_errors(result)
    suggestions = result.data["getSuggestions"]
    assert "action" in suggestions
    assert "adventure" in suggestions
    assert "comedy" not in suggestions


async def test_suggestions_tag_falls_back_to_contains(execute_gql, tag_factory):
    # No tag starts with "ction" but "action" contains it.
    await tag_factory(name="action", tag_count=10)

    result = await execute_gql(
        GET_SUGGESTIONS, {"input": _input("ction", "Tag")}
    )

    assert_no_errors(result)
    assert "action" in result.data["getSuggestions"]


async def test_suggestions_name_aggregates_distinct(execute_gql, video_factory):
    await video_factory(name="alpha-1")
    await video_factory(name="alpha-2")
    await video_factory(name="beta-1")

    result = await execute_gql(
        GET_SUGGESTIONS, {"input": _input("alpha", "Name")}
    )

    assert_no_errors(result)
    suggestions = sorted(result.data["getSuggestions"])
    assert suggestions == ["alpha-1", "alpha-2"]


async def test_suggestions_author_aggregates_distinct(execute_gql, video_factory):
    await video_factory(name="v1", author="alice")
    await video_factory(name="v2", author="alice")
    await video_factory(name="v3", author="bob")

    result = await execute_gql(
        GET_SUGGESTIONS, {"input": _input("ali", "Author")}
    )

    assert_no_errors(result)
    assert result.data["getSuggestions"] == ["alice"]


async def test_suggestions_invalid_suggestion_type(execute_gql, init_db):
    result = await execute_gql(
        GET_SUGGESTIONS, {"input": _input("foo", "NotAField")}
    )
    # Strawberry's enum coercion fails before resolver runs.
    assert result.errors


async def test_suggestions_keyword_too_long(
    execute_gql, init_db, test_settings
):
    too_long = "x" * (test_settings.validation.name_max_length + 1)
    result = await execute_gql(
        GET_SUGGESTIONS, {"input": _input(too_long, "Tag")}
    )
    assert_error_contains(result, "SuggestionInput")
