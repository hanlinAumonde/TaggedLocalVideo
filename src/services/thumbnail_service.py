import asyncio
from functools import lru_cache
import io
import os
import subprocess
from typing import Annotated
from fastapi import Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from starlette.responses import StreamingResponse
from src.config import get_settings
from src.db.models.Video_model import VideoModel
from src.logger import get_logger
from src.services.path_convert_service import AbsolutePath
from src.services.resource_handler.resource_handler_service import get_resource_handler_service

logger = get_logger("thumbnail_service")

class ThumbnailService:
    def __init__(
        self,
    ):
        # Limit concurrent ffmpeg/ffprobe processes to avoid resource exhaustion
        self.process_semaphore = asyncio.Semaphore(
            max(
                get_settings().ffmpeg_semaphore_limit, 
                os.cpu_count() // 2
            )
        )
        self.resourceHandlerService = get_resource_handler_service()
        
    async def get_thumbnail(self, video_id: str, thumbnail_id: str | None = None) -> StreamingResponse:
        if not video_id:
            raise HTTPException(status_code=400, detail="Cannot find thumbnail without video-id")
        else:
            # 1- fetch video metadata from database
            video = await VideoModel.get(video_id) 
            if not video:
                logger.warning(f"Video metadata not found for video_id: {video_id}")
                raise HTTPException(status_code=404, detail="Video not found")

            handler = self.resourceHandlerService.get_handler(video.category)
            video_path = AbsolutePath.from_existing_path(video.path, video.category)
            video_fs_path = video_path.FS_format_path()
            if not handler.file_exists(video_fs_path):
                logger.warning(f"Video file not found at path: {video_fs_path}")
                raise HTTPException(status_code=404, detail="Video file doesn't exist")
            
            no_duration_in_model = video.duration == 0.0 or video.duration is None
                    
            # 2- TODO: find jpeg thumbnail from object storage using thumbnail-id
            if thumbnail_id:
                # get thumbnail data from object storage
                pass
                # get duration if not exists in model
                if no_duration_in_model:
                    video.duration = await self.get_video_duration(video_fs_path)
                    await video.save()

            # 3- video_id exists but thumbnail_id is null/empty - generate thumbnail with ffmpeg
            else:
                thumbnail_bytes = await self.generate_thumbnail(video_fs_path)
                
            return StreamingResponse(
                content=io.BytesIO(thumbnail_bytes),
                media_type="image/jpeg",
                headers={
                    "Cache-Control": "public, max-age=3600"
                }
            )

    async def generate_thumbnail(self, video_path: str, with_duration: bool = True):
        async with self.process_semaphore:
            return await run_in_threadpool(
                self._generate_thumbnail,
                video_path,
                with_duration
            )
    
    async def get_video_duration(self, video_path: str) -> float:
        async with self.process_semaphore:
            try:
                return await run_in_threadpool(
                    self._get_video_duration,
                    video_path
                )
            except Exception as e:
                logger.warning(f"Failed to get duration for {video_path}: {e}")
                return 0.0


    def _generate_thumbnail(self, video_path: str, with_duration: bool = True):
        """
        Generate a thumbnail from video using ffmpeg sync API.
        Captures a frame at 10 seconds into the video.
        """
        try:
            return self._generate_thumbnail_process(video_path, ss=10)
        except Exception as e:
            logger.exception(f"Error generating thumbnail at 10s for {video_path}: {e}")
            # If seeking to 10s fails (video too short), try at 0s
            try:
                return self._generate_thumbnail_process(video_path, ss=0)
            except Exception as e2:
                logger.exception(f"Error generating thumbnail at 0s for {video_path}: {e2}")
                raise HTTPException(status_code=500, detail="Failed to generate thumbnail")


    def _generate_thumbnail_process(self, video_path: str, ss: float) -> bytes:
        """
        Construct an FFmpeg command to generate a thumbnail from the video at the specified timestamp.
        """
        command = [
            "ffmpeg",
            "-loglevel", "error",
            "-ss", str(ss),
            "-i", video_path,
            "-frames:v", "1",
            "-f", "image2",
            "-vcodec", "mjpeg",
            "-vf", "scale=320:-1",
            "pipe:1"
        ]

        process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        image_data = process.stdout

        if not image_data:
            raise HTTPException(status_code=500, detail="Failed to generate thumbnail")

        return image_data

    def _get_video_duration(self, video_path: str) -> float:
        """
        Get the duration of the video in seconds using ffprobe.
        """
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        return float(result.stdout)

@lru_cache()
def get_thumbnail_service() -> ThumbnailService:
    return ThumbnailService()

ThumbnailServiceDep = Annotated[ThumbnailService, Depends(get_thumbnail_service)]