"""Tests for ``searchSeriesByPrefix`` and ``getSeriesVideos`` queries."""

import pytest

from tests.graphql.helpers import (
    GET_SERIES_VIDEOS,
    SEARCH_SERIES_BY_PREFIX,
    assert_no_errors,
)


pytestmark = pytest.mark.query


# ----------------------------- searchSeriesByPrefix ----------------------------

async def test_search_series_by_prefix_returns_distinct(
    execute_gql, video_factory
):
    await video_factory(name="v1", seriesName="Sherlock", seriesOrder=1)
    await video_factory(name="v2", seriesName="Sherlock", seriesOrder=2)
    await video_factory(name="v3", seriesName="Stranger Things", seriesOrder=1)

    result = await execute_gql(
        SEARCH_SERIES_BY_PREFIX, {"prefix": "S", "limit": 10}
    )

    assert_no_errors(result)
    series = sorted(result.data["searchSeriesByPrefix"])
    assert series == ["Sherlock", "Stranger Things"]


async def test_search_series_by_prefix_case_insensitive(execute_gql, video_factory):
    await video_factory(name="v1", seriesName="Sherlock", seriesOrder=1)

    result = await execute_gql(
        SEARCH_SERIES_BY_PREFIX, {"prefix": "sher", "limit": 10}
    )

    assert_no_errors(result)
    assert result.data["searchSeriesByPrefix"] == ["Sherlock"]


async def test_search_series_by_prefix_no_match(execute_gql, video_factory):
    await video_factory(name="v1", seriesName="Sherlock", seriesOrder=1)

    result = await execute_gql(
        SEARCH_SERIES_BY_PREFIX, {"prefix": "Z", "limit": 10}
    )

    assert_no_errors(result)
    assert result.data["searchSeriesByPrefix"] == []


async def test_search_series_by_prefix_zero_limit(execute_gql, init_db):
    result = await execute_gql(
        SEARCH_SERIES_BY_PREFIX, {"prefix": "any", "limit": 0}
    )
    assert_no_errors(result)
    assert result.data["searchSeriesByPrefix"] == []


async def test_search_series_by_prefix_negative_limit(execute_gql, init_db):
    result = await execute_gql(
        SEARCH_SERIES_BY_PREFIX, {"prefix": "any", "limit": -1}
    )
    assert_no_errors(result)
    assert result.data["searchSeriesByPrefix"] == []


# -------------------------------- getSeriesVideos ------------------------------

async def test_get_series_videos_returns_in_order(execute_gql, video_factory):
    await video_factory(name="ep3", seriesName="MyShow", seriesOrder=3)
    await video_factory(name="ep1", seriesName="MyShow", seriesOrder=1)
    await video_factory(name="ep2", seriesName="MyShow", seriesOrder=2)
    await video_factory(name="other", seriesName="OtherShow", seriesOrder=1)

    result = await execute_gql(GET_SERIES_VIDEOS, {"name": "MyShow"})

    assert_no_errors(result)
    names = [v["name"] for v in result.data["getSeriesVideos"]]
    assert names == ["ep1", "ep2", "ep3"]


async def test_get_series_videos_empty_name(execute_gql, init_db):
    result = await execute_gql(GET_SERIES_VIDEOS, {"name": ""})
    assert_no_errors(result)
    assert result.data["getSeriesVideos"] == []


async def test_get_series_videos_excludes_invalid_categories(
    execute_gql, video_factory, monkeypatch, test_settings
):
    await video_factory(name="ep1", seriesName="X", seriesOrder=1)
    monkeypatch.setattr(test_settings, "resource_paths", {})

    result = await execute_gql(GET_SERIES_VIDEOS, {"name": "X"})

    assert_no_errors(result)
    assert result.data["getSeriesVideos"] == []


async def test_get_series_videos_unknown_series(execute_gql, init_db):
    result = await execute_gql(GET_SERIES_VIDEOS, {"name": "DoesNotExist"})
    assert_no_errors(result)
    assert result.data["getSeriesVideos"] == []
