import io
import os
from typing import Annotated
import aiofiles
from fastapi.concurrency import run_in_threadpool
from fastapi import Depends, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from src.db.models.Video_model import VideoModel
from src.logger import get_logger
from src.resolvers.resolver_utils import resolver_utils
from src.resolvers.thumbnail_resolver import ThumbnailResolverDep

logger = get_logger("video_stream_resolver")

class VideoResolver:
    def __init__(
        self,
        thumbnailResolver: ThumbnailResolverDep
    ):
        self.thumbnailResolver = thumbnailResolver

    async def video_stream_resolver(self,video_id: str, request: Request) -> StreamingResponse:
        """
        Handles video streaming requests and supports Range requests (for drag-and-drop playback in Video.js).

        Args:
            video_id: The MongoDB ID of the video
            request: A FastAPI Request object used to retrieve the range header

        Returns: 
            StreamingResponse: The video stream response
        """
        video = await VideoModel.get(video_id)
        if not video:
            raise HTTPException(status_code=404, detail="video metadata doesn't exist")

        video_path = resolver_utils().to_mounted_path(video.path)
        if not os.path.exists(video_path):
            raise HTTPException(status_code=404, detail="video file doesn't exist")

        file_size = os.path.getsize(video_path)

        range_header = request.headers.get("Range")

        try:
            if range_header:
                # bytes=start-end
                byte_range = range_header.replace("bytes=", "").split("-")
                start = int(byte_range[0]) if byte_range[0] else 0
                end = int(byte_range[1]) if byte_range[1] else file_size - 1

                # Ensure the scope is valid
                if start >= file_size or end >= file_size:
                    raise HTTPException(
                        status_code=416,
                        detail="The requested scope is invalid.",
                        headers={"Content-Range": f"bytes */{file_size}"}
                    )

                content_length = end - start + 1

                return StreamingResponse(
                    self.iter_file(video_path, 1024*1024, start, content_length),
                    status_code=206,
                    headers={
                        "Content-Range": f"bytes {start}-{end}/{file_size}",
                        "Accept-Ranges": "bytes",
                        "Content-Length": str(content_length),
                        "Content-Type": resolver_utils().get_video_mime_type(video_path),
                    },
                    media_type=resolver_utils().get_video_mime_type(video_path)
                )

            else:
                return StreamingResponse(
                    self.iter_file(video_path, chunk_size=1024*1024, with_range=False),
                    headers={
                        "Accept-Ranges": "bytes",
                        "Content-Length": str(file_size),
                        "Content-Type": resolver_utils().get_video_mime_type(video_path),
                    },
                    media_type=resolver_utils().get_video_mime_type(video_path)
                )
        except Exception as e:
            logger.error(f"Error while processing video stream request: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
        
    async def iter_file(self, video_path: str, chunk_size: int = 1024*1024, start: int = 0, content_length: int | None = None, with_range: bool = True):
        async with aiofiles.open(video_path, "rb") as video_file:
            if with_range:
                await video_file.seek(start)
                remaining = content_length
                while remaining > 0:
                    chunk = await video_file.read(min(chunk_size, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk
            else:
                while chunk := await video_file.read(chunk_size):
                    yield chunk          
    
    async def get_thumbnail_and_duration(self, video_id: str, thumbnail_id: str | None = None) -> StreamingResponse:
        if not video_id:
            raise HTTPException(status_code=400, detail="Cannot find thumbnail without video-id")
        else:
            # 1- fetch video metadata from database
            video = await VideoModel.get(video_id) 
            if not video:
                logger.warning(f"Video metadata not found for video_id: {video_id}")
                raise HTTPException(status_code=404, detail="Video not found")

            video_path = resolver_utils().to_mounted_path(video.path)
            if not os.path.exists(video_path):
                logger.warning(f"Video file not found at path: {video_path}")
                raise HTTPException(status_code=404, detail="Video file doesn't exist")
            
            no_duration_in_model = video.duration == 0.0 or video.duration is None
                    
            # 2- TODO: find jpeg thumbnail from object storage using thumbnail-id
            if thumbnail_id:
                # get thumbnail data from object storage
                pass
                # get duration if not exists in model
                if no_duration_in_model:
                    video.duration = await run_in_threadpool(
                        self.thumbnailResolver.get_video_duration,
                        video_path
                    )
                    await video.save()

            # 3- video_id exists but thumbnail_id is null/empty - generate thumbnail with ffmpeg
            else:
                thumbnail_bytes, duration = await run_in_threadpool(
                    self.thumbnailResolver.generate_thumbnail_and_duration, 
                    video_path, 
                    with_duration=no_duration_in_model
                )

                if duration and no_duration_in_model:
                    video.duration = duration
                    await video.save()
                
            headers = {
                "X-Video-Duration": str(video.duration or duration or 0.0),
                "Cache-Control": "public, max-age=3600"
            }

            return StreamingResponse(
                content=io.BytesIO(thumbnail_bytes),
                media_type="image/jpeg",
                headers=headers
            )

def get_video_resolver(thumbnailResolver: ThumbnailResolverDep):
    return VideoResolver(thumbnailResolver)

VideoResolverDep = Annotated[VideoResolver, Depends(get_video_resolver)]
