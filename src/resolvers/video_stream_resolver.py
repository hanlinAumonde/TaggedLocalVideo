from typing import Annotated
from fastapi import Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from src.db.models.Video_model import VideoModel
from src.logger import get_logger
from src.services.path_convert_service import AbsolutePath
from src.services.resource_handler.base_resource_handler import BaseResourceHandler
from src.services.resource_handler.resource_handler_service import get_resource_handler_service

logger = get_logger("video_stream_resolver")

class VideoResolver:
    def __init__(
        self,
    ):
        self.resourceHandlerService = get_resource_handler_service()

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

        handler = self.resourceHandlerService.get_handler(video.category)
        video_fs_path = AbsolutePath.from_existing_path(video.path, video.category).FS_format_path()
        if not handler.file_exists(video_fs_path):
            raise HTTPException(status_code=404, detail="video file doesn't exist")

        file_size = handler.get_size(video_fs_path)

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
                    self._iter_file_chunks(handler, video_fs_path, 1024*1024, start, content_length),
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
                    self._iter_file_chunks(handler, video_fs_path, 1024*1024, 0, int(file_size)),
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

    async def _iter_file_chunks(
        self, handler: BaseResourceHandler, path: str,
        chunk_size: int, start: int, content_length: int
    ):
        remaining = content_length
        offset = start
        while remaining > 0:
            read_size = min(chunk_size, remaining)
            chunk = await handler.read_file_chunk(path, offset, read_size)
            if not chunk:
                break
            offset += len(chunk)
            remaining -= len(chunk)
            yield chunk

    def get_video_mime_type(self, file_path: str) -> str:
        """
        Returns the correct MIME type based on the file extension.

        Args:
            file_path: Video file path

        Returns:
            str: MIME type string
        """
        return "video/mp4"


def get_video_resolver():
    return VideoResolver()

VideoResolverDep = Annotated[VideoResolver, Depends(get_video_resolver)]
