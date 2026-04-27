"""Tests for the ``updateVideoMetadata`` mutation."""

from bson import ObjectId
import pytest

from src.db.models.Video_model import VideoModel
from src.db.models.VideoTag_model import VideoTagModel
from tests.graphql.helpers import (
    UPDATE_VIDEO_METADATA,
    assert_error_contains,
    assert_no_errors,
    make_update_input,
)


pytestmark = pytest.mark.mutation


# ------------------------- Field-level updates -----------------------------

async def test_update_video_name_and_loved(execute_gql, video_factory):
    video = await video_factory(name="old", loved=False)

    payload = make_update_input(
        str(video.id), name="new-name", loved=True, tags=[]
    )
    result = await execute_gql(UPDATE_VIDEO_METADATA, {"input": payload})

    assert_no_errors(result)
    body = result.data["updateVideoMetadata"]
    assert body["success"] is True
    assert body["video"]["name"] == "new-name"
    assert body["video"]["loved"] is True

    refreshed = await VideoModel.get(video.id)
    assert refreshed.name == "new-name"
    assert refreshed.loved is True


async def test_update_video_introduction_and_author(execute_gql, video_factory):
    video = await video_factory(name="v", author="old-author", introduction="")

    payload = make_update_input(
        str(video.id),
        introduction="New plot summary",
        author="alice",
        tags=[],
    )
    result = await execute_gql(UPDATE_VIDEO_METADATA, {"input": payload})

    assert_no_errors(result)
    body = result.data["updateVideoMetadata"]
    assert body["video"]["author"] == "alice"
    assert body["video"]["introduction"] == "New plot summary"


# ------------------------- Tag count side-effects --------------------------

async def test_update_video_tags_increments_new_decrements_old(
    execute_gql, video_factory, tag_factory
):
    await tag_factory(name="kept", tag_count=1)
    await tag_factory(name="removed", tag_count=1)
    video = await video_factory(name="v", tags=["kept", "removed"])

    # Replace tags: keep "kept", drop "removed", add "added".
    payload = make_update_input(str(video.id), tags=["kept", "added"])
    result = await execute_gql(UPDATE_VIDEO_METADATA, {"input": payload})
    assert_no_errors(result)

    kept = await VideoTagModel.find_one({"name": "kept"})
    removed = await VideoTagModel.find_one({"name": "removed"})
    added = await VideoTagModel.find_one({"name": "added"})

    assert kept.tag_count == 1
    assert removed is None  # decremented to 0 → deleted
    assert added.tag_count == 1


# ----------------------------- Series field --------------------------------

async def test_update_video_series_clear(execute_gql, video_factory):
    video = await video_factory(
        name="v", seriesName="Foo", seriesOrder=1
    )

    payload = make_update_input(
        str(video.id),
        tags=[],
        series={"clear": True, "name": None, "orders": []},
    )
    result = await execute_gql(UPDATE_VIDEO_METADATA, {"input": payload})

    assert_no_errors(result)
    body = result.data["updateVideoMetadata"]
    assert body["video"]["seriesName"] is None
    assert body["video"]["seriesOrder"] is None

    refreshed = await VideoModel.get(video.id)
    assert refreshed.seriesName is None
    assert refreshed.seriesOrder is None


async def test_update_video_series_rewrites_ordering(execute_gql, video_factory):
    a = await video_factory(name="A", seriesName="MyShow", seriesOrder=1)
    b = await video_factory(name="B", seriesName="MyShow", seriesOrder=2)

    payload = make_update_input(
        str(a.id),
        tags=[],
        series={
            "name": "MyShow",
            "clear": False,
            "orders": [
                {"videoId": str(a.id), "order": 2},
                {"videoId": str(b.id), "order": 1},
            ],
        },
    )
    result = await execute_gql(UPDATE_VIDEO_METADATA, {"input": payload})

    assert_no_errors(result)
    a_refreshed = await VideoModel.get(a.id)
    b_refreshed = await VideoModel.get(b.id)
    assert a_refreshed.seriesOrder == 2
    assert b_refreshed.seriesOrder == 1


async def test_update_video_series_orders_missing_current_video(
    execute_gql, video_factory
):
    a = await video_factory(name="A", seriesName="S", seriesOrder=1)
    b = await video_factory(name="B", seriesName="S", seriesOrder=2)

    payload = make_update_input(
        str(a.id),
        tags=[],
        series={
            "name": "S",
            "clear": False,
            "orders": [{"videoId": str(b.id), "order": 1}],
        },
    )
    result = await execute_gql(UPDATE_VIDEO_METADATA, {"input": payload})
    assert_error_contains(result, "orders")


async def test_update_video_series_duplicate_order(execute_gql, video_factory):
    a = await video_factory(name="A", seriesName="S", seriesOrder=1)
    b = await video_factory(name="B", seriesName="S", seriesOrder=2)

    payload = make_update_input(
        str(a.id),
        tags=[],
        series={
            "name": "S",
            "clear": False,
            "orders": [
                {"videoId": str(a.id), "order": 1},
                {"videoId": str(b.id), "order": 1},
            ],
        },
    )
    result = await execute_gql(UPDATE_VIDEO_METADATA, {"input": payload})
    assert_error_contains(result, "order")


async def test_update_video_series_other_video_not_in_target_series(
    execute_gql, video_factory
):
    a = await video_factory(name="A", seriesName="S", seriesOrder=1)
    foreign = await video_factory(name="F", seriesName="OtherShow", seriesOrder=1)

    payload = make_update_input(
        str(a.id),
        tags=[],
        series={
            "name": "S",
            "clear": False,
            "orders": [
                {"videoId": str(a.id), "order": 1},
                {"videoId": str(foreign.id), "order": 2},
            ],
        },
    )
    result = await execute_gql(UPDATE_VIDEO_METADATA, {"input": payload})
    assert_error_contains(result, "do not currently belong")


async def test_update_video_series_invalid_object_id_in_orders(
    execute_gql, video_factory
):
    a = await video_factory(name="A", seriesName="S", seriesOrder=1)

    payload = make_update_input(
        str(a.id),
        tags=[],
        series={
            "name": "S",
            "clear": False,
            "orders": [
                {"videoId": str(a.id), "order": 1},
                {"videoId": "not-an-oid", "order": 2},
            ],
        },
    )
    result = await execute_gql(UPDATE_VIDEO_METADATA, {"input": payload})
    assert_error_contains(result, "orders")


# ----------------------------- Validation errors ---------------------------

async def test_update_video_metadata_name_too_long(
    execute_gql, video_factory, test_settings
):
    video = await video_factory(name="v")
    too_long = "x" * (test_settings.validation.name_max_length + 1)

    payload = make_update_input(str(video.id), name=too_long, tags=[])
    result = await execute_gql(UPDATE_VIDEO_METADATA, {"input": payload})
    assert_error_contains(result, "UpdateVideoMetadataInput")


async def test_update_video_metadata_too_many_tags(
    execute_gql, video_factory, test_settings
):
    video = await video_factory(name="v")
    too_many = [f"t{i}" for i in range(test_settings.validation.max_tags_count + 1)]

    payload = make_update_input(str(video.id), tags=too_many)
    result = await execute_gql(UPDATE_VIDEO_METADATA, {"input": payload})
    assert_error_contains(result, "UpdateVideoMetadataInput")


async def test_update_video_metadata_missing_input(execute_gql, init_db):
    result = await execute_gql(UPDATE_VIDEO_METADATA, {})
    assert_error_contains(result, "input")


async def test_update_video_metadata_unknown_video_id(execute_gql, init_db):
    # Resolver only returns success/raises if the document was found.
    # When not found, the resolver simply returns nothing — the GraphQL
    # response will have ``updateVideoMetadata`` set to None because the
    # non-null result type is breached.
    payload = make_update_input(str(ObjectId()), tags=[])
    result = await execute_gql(UPDATE_VIDEO_METADATA, {"input": payload})
    assert result.errors  # cannot return null for non-null result type
