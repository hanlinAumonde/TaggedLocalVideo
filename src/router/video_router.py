from typing import Annotated
from fastapi import APIRouter, Depends, Request

from src.resolvers.video_stream_resolver import VideoResolver

def get_video_resolver():
    return VideoResolver()

VideoResolverDep = Annotated[VideoResolver, Depends(get_video_resolver)]

router = APIRouter(prefix="/video")

@router.get("/stream/{video_id}")
async def stream_video(video_id: str, request: Request, videoResolverDep: VideoResolverDep):
    """video stream endpoint"""
    return await videoResolverDep.video_stream_resolver(video_id, request)

@router.get("/thumbnail")
async def get_thumbnail(video_id: str, videoResolverDep: VideoResolverDep, thumbnail_id: str | None = None):
    return await videoResolverDep.get_thumbnail(video_id, thumbnail_id)