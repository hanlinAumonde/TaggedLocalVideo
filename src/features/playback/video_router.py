from fastapi import APIRouter, Request
from src.context import ThumbnailServiceDep, VideoStreamServiceDep

router = APIRouter(prefix="/video")

@router.get("/stream/{video_id}")
async def stream_video(video_id: str, request: Request, video_stream_service: VideoStreamServiceDep):
    return await video_stream_service.video_stream_resolver(video_id, request)

@router.get("/thumbnail")
async def get_thumbnail(thumbnailServiceDep: ThumbnailServiceDep, video_id: str):
    return await thumbnailServiceDep.get_thumbnail(video_id)