from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from src.config import Settings
from src.db.models.Video_model import VideoModel
from src.services.thumbnail_service import ThumbnailService


# -----------------------------------------------------------------------
# ------------------- Missing video / file edge cases --------------------
# -----------------------------------------------------------------------

async def test_get_thumbnail_empty_id_raises_400(thumb_svc, init_db):
    with pytest.raises(HTTPException) as exc_info:
        await thumb_svc.get_thumbnail("")
    assert exc_info.value.status_code == 400


async def test_get_thumbnail_unknown_id_raises_404(thumb_svc, init_db):
    from bson import ObjectId
    with pytest.raises(HTTPException) as exc_info:
        await thumb_svc.get_thumbnail(str(ObjectId()))
    assert exc_info.value.status_code == 404


async def test_get_thumbnail_file_missing_raises_404(
    thumb_svc, init_db, video_factory, handler,
):
    video = await video_factory(name="v")
    handler.file_exists.return_value = False

    with pytest.raises(HTTPException) as exc_info:
        await thumb_svc.get_thumbnail(str(video.id))
    assert exc_info.value.status_code == 404


# -----------------------------------------------------------------------
# ------------------- On-the-fly generation (no storage) -----------------
# -----------------------------------------------------------------------

async def test_generate_on_the_fly_returns_jpeg_response(
    thumb_svc, init_db, video_factory, ffmpeg_svc,
):
    video = await video_factory(name="v", duration=0.0)
    response = await thumb_svc.get_thumbnail(str(video.id))

    assert response.media_type == "image/jpeg"
    ffmpeg_svc.generate_thumbnail.assert_called_once()
    # Duration was 0 → should also have fetched duration.
    ffmpeg_svc.get_video_duration.assert_called_once()

    refreshed = await VideoModel.get(video.id)
    assert refreshed.duration == 120.0


async def test_skip_duration_when_already_set(
    thumb_svc, init_db, video_factory, ffmpeg_svc,
):
    video = await video_factory(name="v", duration=60.0)
    await thumb_svc.get_thumbnail(str(video.id))

    ffmpeg_svc.get_video_duration.assert_not_called()


# -----------------------------------------------------------------------
# ------------------- Stored thumbnail hit -------------------------------
# -----------------------------------------------------------------------

async def test_stored_thumbnail_hit_returns_without_generating(
    thumb_svc_with_storage, init_db, video_factory, ffmpeg_svc,
):
    video = await video_factory(name="v", thumbnail="thumbs/v.jpg")

    storage = thumb_svc_with_storage._storage_handler
    storage.file_exists.return_value = True
    storage.get_size.return_value = 1024
    storage.read_file_chunk = AsyncMock(return_value=b"STORED-JPEG")

    response = await thumb_svc_with_storage.get_thumbnail(str(video.id))

    assert response.media_type == "image/jpeg"
    ffmpeg_svc.generate_thumbnail.assert_not_called()


async def test_stored_thumbnail_miss_falls_back_to_generation(
    thumb_svc_with_storage, init_db, video_factory, ffmpeg_svc,
):
    video = await video_factory(name="v", thumbnail="thumbs/v.jpg")

    storage = thumb_svc_with_storage._storage_handler
    # The video file check handler returns True, but the thumbnail doesn't exist.
    storage.file_exists.return_value = False

    response = await thumb_svc_with_storage.get_thumbnail(str(video.id))

    assert response.media_type == "image/jpeg"
    ffmpeg_svc.generate_thumbnail.assert_called_once()
    storage.write_file.assert_called_once()


# -----------------------------------------------------------------------
# ------------------- Storage init edge cases ----------------------------
# -----------------------------------------------------------------------

def test_storage_init_category_not_found(handler_svc, ffmpeg_svc):
    handler_svc.get_handler.side_effect = ValueError("category not found")
    settings = Settings.model_validate({
        "resource_paths": {"Test-category": {"Test-resource": "/test"}},
        "thumbnail_config": {
            "storage_category": "NonExistent",
            "storage_pseudo_name": "SomeName",
        },
    })
    svc = ThumbnailService(
        resource_handler_service=handler_svc,
        ffmpeg_service=ffmpeg_svc,
        settings=settings,
    )
    assert svc._storage_handler is None


# -----------------------------------------------------------------------
# ---- Read/store thumbnail exception handling ---------------------------
# -----------------------------------------------------------------------

async def test_read_stored_thumbnail_exception_returns_none(
    thumb_svc_with_storage, init_db, video_factory, ffmpeg_svc,
):
    video = await video_factory(name="v", thumbnail="thumbs/v.jpg")

    storage = thumb_svc_with_storage._storage_handler
    storage.file_exists.side_effect = RuntimeError("disk failure")

    response = await thumb_svc_with_storage.get_thumbnail(str(video.id))
    assert response.media_type == "image/jpeg"
    ffmpeg_svc.generate_thumbnail.assert_called_once()


async def test_store_thumbnail_exception_does_not_raise(
    thumb_svc_with_storage, init_db, video_factory, ffmpeg_svc,
):
    video = await video_factory(name="v")

    storage = thumb_svc_with_storage._storage_handler
    storage.file_exists.return_value = False
    storage.write_file = AsyncMock(side_effect=RuntimeError("write failure"))

    response = await thumb_svc_with_storage.get_thumbnail(str(video.id))
    assert response.media_type == "image/jpeg"
