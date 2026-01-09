from typing import Annotated
from fastapi import APIRouter, Depends, Request
#from pydantic import BaseModel

from src.resolvers.video_stream_resolver import VideoResolver

def get_video_resolver():
    return VideoResolver()

VideoResolverDep = Annotated[VideoResolver, Depends(get_video_resolver)]

router = APIRouter()

@router.get("/video/stream/{video_id}")
async def stream_video(video_id: str, request: Request, videoResolverDep: VideoResolverDep):
    """video stream endpoint"""
    return await videoResolverDep.video_stream_resolver(video_id, request)

# class ThumbnailsInput(BaseModel):
#     ids: list[str]

# @router.get("/thumbnails")
# async def get_thumbnails_batch(input:ThumbnailsInput):
#     return [] #[{"id":"thumbnailID","bytes":thumbnails_bytes}]