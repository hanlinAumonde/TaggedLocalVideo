import os
import aiofiles
from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from src.db.models.Video_model import VideoModel
from src.resolvers.resolver_utils import to_mounted_path


class VideoResolver:

    async def video_stream_resolver(self,video_id: str, request: Request):
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

        video_path = to_mounted_path(video.path)
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
                    "Content-Type": self.get_video_mime_type(video_path),
                },
                media_type=self.get_video_mime_type(video_path)
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
                    "Content-Type": self.get_video_mime_type(video_path),
                },
                media_type=self.get_video_mime_type(video_path)
            )


    def get_video_mime_type(self,file_path: str) -> str:
        """
        Returns the correct MIME type based on the file extension.

        Args:
            file_path: Video file path

        Returns:
            str: MIME type string
        """
        ext = os.path.splitext(file_path)[1].lower()
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
    
    async def get_thumbnail(self,video_id:str,thumbnail_id:str) -> FileResponse | None:
        if thumbnail_id:
            pass # TODO: find jpeg thumbnail from file system using thumbnail-id
        elif not video_id:
            raise HTTPException(status_code=404, detail="Cannot find thumbnail without video-id")
        else:
            return None
            # TODO:
            # video-id is not null and thumbnail-id is null
            # using for example ffmpeg to generate a thumbnail and store it in the file system, and update db
            # return the jpeg file
