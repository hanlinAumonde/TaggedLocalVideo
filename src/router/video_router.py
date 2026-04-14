from fastapi import APIRouter, Request
from src.resolvers.video_stream_resolver import VideoResolverDep
from src.services.thumbnail_service import ThumbnailServiceDep

router = APIRouter(prefix="/video")

@router.get("/stream/{video_id}")
async def stream_video(video_id: str, request: Request, videoResolverDep: VideoResolverDep):
    """video stream endpoint"""
    return await videoResolverDep.video_stream_resolver(video_id, request)

@router.get("/thumbnail")
async def get_thumbnail(thumbnailServiceDep: ThumbnailServiceDep, video_id: str):
    return await thumbnailServiceDep.get_thumbnail(video_id)