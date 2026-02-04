import asyncio
from functools import lru_cache
import os
import subprocess
from fastapi import HTTPException
from fastapi.concurrency import run_in_threadpool

from src.config import get_settings
from src.logger import get_logger

# Limit concurrent ffmpeg/ffprobe processes to avoid resource exhaustion
_process_semaphore = asyncio.Semaphore(
    max(
        get_settings().ffmpeg_semaphore_limit, 
        os.cpu_count() // 2
    )
)

logger = get_logger("thumbnail_resolver")

class ThumbnailResolver:

    async def generate_thumbnail(self, video_path: str, with_duration: bool = True):
        async with _process_semaphore:
            return await run_in_threadpool(
                self._generate_thumbnail,
                video_path,
                with_duration
            )
    
    async def get_video_duration(self, video_path: str) -> float:
        async with _process_semaphore:
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
            logger.error(f"Error generating thumbnail at 10s for {video_path}: {e}")
            # If seeking to 10s fails (video too short), try at 0s
            try:
                return self._generate_thumbnail_process(video_path, ss=0)
            except Exception as e2:
                logger.error(f"Error generating thumbnail at 0s for {video_path}: {e2}")
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
def get_thumbnail_resolver():
    return ThumbnailResolver()