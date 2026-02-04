from fastapi import APIRouter, Request

from src.resolvers.video_stream_resolver import VideoResolverDep

router = APIRouter(prefix="/video")

@router.get("/stream/{video_id}")
async def stream_video(video_id: str, request: Request, videoResolverDep: VideoResolverDep):
    """video stream endpoint"""
    return await videoResolverDep.video_stream_resolver(video_id, request)

@router.get("/thumbnail")
async def get_thumbnail(videoResolverDep: VideoResolverDep, video_id: str, thumbnail_id: str | None = None):
    return await videoResolverDep.get_thumbnail(video_id, thumbnail_id)