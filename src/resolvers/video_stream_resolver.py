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

            async def iterfile():
                async with aiofiles.open(video_path, "rb") as video_file:
                    await video_file.seek(start)
                    remaining = content_length
                    chunk_size = 1024 * 1024 # 1MB chunks

                    while remaining > 0:
                        chunk = await video_file.read(min(chunk_size, remaining))
                        if not chunk:
                            break
                        remaining -= len(chunk)
                        yield chunk

            return StreamingResponse(
                iterfile(),
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
            # without Range header, return an entire video
            async def iterfile():
                async with aiofiles.open(video_path, "rb") as video_file:
                    chunk_size = 1024 * 1024 # 1MB chunks
                    while chunk := await video_file.read(chunk_size):
                        yield chunk

            return StreamingResponse(
                iterfile(),
                headers={
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(file_size),
                    "Content-Type": resolver_utils().get_video_mime_type(video_path),
                },
                media_type=resolver_utils().get_video_mime_type(video_path)
            )
        
    
    async def get_thumbnail(self, video_id: str, thumbnail_id: str | None = None) -> Response:
        if thumbnail_id:
            pass  # TODO: find jpeg thumbnail from file system (or object storage) using thumbnail-id

        if not video_id:
            raise HTTPException(status_code=400, detail="Cannot find thumbnail without video-id")

        # video_id exists but thumbnail_id is null/empty - generate thumbnail with ffmpeg
        video = await VideoModel.get(video_id)
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")

        video_path = resolver_utils().to_mounted_path(video.path)
        if not os.path.exists(video_path):
            raise HTTPException(status_code=404, detail="Video file doesn't exist")

        thumbnail_bytes = await run_in_threadpool(self.thumbnailResolver.generate_thumbnail, video_path)
        return Response(
            content=thumbnail_bytes,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=3600"}
        )

def get_video_resolver(thumbnailResolver: ThumbnailResolverDep):
    return VideoResolver(thumbnailResolver)

VideoResolverDep = Annotated[VideoResolver, Depends(get_video_resolver)]
