import os
import aiofiles
from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse
from src.db.models.Video_model import VideoModel


async def video_stream_resolver(video_id: str, request: Request):
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

    video_path = video.path
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


        # Return partial response (206 Partial Content)
        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
            "Content-Type": get_video_mime_type(video_path),
        }

        return StreamingResponse(
            iterfile(),
            status_code=206,
            headers=headers,
            media_type=get_video_mime_type(video_path)
        )

    else:
        # without Range header, return an entire video
        async def iterfile():
            async with aiofiles.open(video_path, "rb") as video_file:
                chunk_size = 1024 * 1024 # 1MB chunks
                while chunk := await video_file.read(chunk_size):
                    yield chunk


        headers = {
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
            "Content-Type": get_video_mime_type(video_path),
        }

        return StreamingResponse(
            iterfile(),
            headers=headers,
            media_type=get_video_mime_type(video_path)
        )


def get_video_mime_type(file_path: str) -> str:
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