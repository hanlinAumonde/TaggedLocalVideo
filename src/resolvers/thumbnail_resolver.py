import subprocess
from typing_extensions import Annotated
from fastapi import Depends, HTTPException

from src.logger import get_logger

logger = get_logger("thumbnail_resolver")

class ThumbnailResolver:

    def generate_thumbnail(self, video_path: str) -> bytes:
        """
        Generate a thumbnail from video using ffmpeg sync API.
        Captures a frame at 5 seconds into the video.
        """
        try:
            return self._process_ffmpeg(video_path, ss=10)
        except Exception as e:
            logger.error(f"Error generating thumbnail at 10s for {video_path}: {e}")
            # If seeking to 10s fails (video too short), try at 0s
            try:
                return self._process_ffmpeg(video_path, ss=0)
            except Exception as e2:
                logger.error(f"Error generating thumbnail at 0s for {video_path}: {e2}")
                raise HTTPException(status_code=500, detail="Failed to generate thumbnail")

    def _process_ffmpeg(self, video_path: str, ss: float) -> bytes:
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
            "-aspect", "16:9",
            "-vf", "scale=320:-1",
            "pipe:1"
        ]

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        if result.returncode != 0 or not result.stdout:
            raise HTTPException(status_code=500, detail="Failed to generate thumbnail")

        return result.stdout

  
def get_thumbnail_resolver():
    return ThumbnailResolver()

ThumbnailResolverDep = Annotated[ThumbnailResolver, Depends(get_thumbnail_resolver)]