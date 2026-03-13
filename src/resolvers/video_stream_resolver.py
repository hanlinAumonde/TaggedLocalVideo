import os
from typing import Annotated
import aiofiles
from fastapi import Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from src.db.models.Video_model import VideoModel
from src.logger import get_logger
from src.services.path_convert_service import AbsolutePath, get_path_service

logger = get_logger("video_stream_resolver")

class VideoResolver:
    def __init__(
        self,
    ):
        self.pathHepler = get_path_service()

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

        video_path = AbsolutePath.from_existing_path(video.path)
        video_fs_path = video_path.FS_format_path()
        if not os.path.exists(video_fs_path):
            raise HTTPException(status_code=404, detail="video file doesn't exist")

        file_size = os.path.getsize(video_fs_path)

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
                    self.iter_file(video_fs_path, 1024*1024, start, content_length),
                    status_code=206,
                    headers={
                        "Content-Range": f"bytes {start}-{end}/{file_size}",
                        "Accept-Ranges": "bytes",
                        "Content-Length": str(content_length),
                        "Content-Type": self.get_video_mime_type(video_fs_path),
                    },
                    media_type=self.get_video_mime_type(video_fs_path)
                )

            else:
                return StreamingResponse(
                    self.iter_file(video_fs_path, chunk_size=1024*1024, with_range=False),
                    headers={
                        "Accept-Ranges": "bytes",
                        "Content-Length": str(file_size),
                        "Content-Type": self.get_video_mime_type(video_fs_path),
                    },
                    media_type=self.get_video_mime_type(video_fs_path)
                )
        except Exception as e:
            logger.exception(f"Error while processing video stream request: {e}")
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
    
    
    def get_video_mime_type(self, file_path: str) -> str:
        """
        Returns the correct MIME type based on the file extension.

        Args:
            file_path: Video file path

        Returns:
            str: MIME type string
        """
        ext = self.pathHepler.get_file_extension(file_path).lower()
        mime_types = {
            ".mp4": "video/mp4",
            ".webm": "video/webm",
            ".ogg": "video/ogg",
            ".ogv": "video/ogg",
            ".avi": "video/x-msvideo",
            ".mov": "video/quicktime",
            ".wmv": "video/x-ms-wmv",
            ".flv": "video/x-flv",
            ".mkv": "video/x-matroska",
            ".m4v": "video/x-m4v",
            ".mpg": "video/mpeg",
            ".mpeg": "video/mpeg",
        }
        return mime_types.get(ext, "video/mp4")


def get_video_resolver():
    return VideoResolver()

VideoResolverDep = Annotated[VideoResolver, Depends(get_video_resolver)]
