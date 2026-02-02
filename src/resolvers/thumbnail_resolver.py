import json
import subprocess
from typing_extensions import Annotated
from fastapi import Depends, HTTPException

from src.logger import get_logger

logger = get_logger("thumbnail_resolver")

class ThumbnailResolver:

    def generate_thumbnail_and_duration(self, video_path: str, with_duration: bool = True):
        """
        Generate a thumbnail from video using ffmpeg sync API.
        Captures a frame at 10 seconds into the video.
        """
        try:
            if with_duration:
                return self._generate_thumbnail(video_path, ss=10), self.get_video_duration(video_path)
            else:
                return self._generate_thumbnail(video_path, ss=10), None
        except Exception as e:
            logger.error(f"Error generating thumbnail at 10s for {video_path}: {e}")
            # If seeking to 10s fails (video too short), try at 0s
            try:
                if with_duration:
                    return self._generate_thumbnail(video_path, ss=0), self.get_video_duration(video_path)
                else:
                    return self._generate_thumbnail(video_path, ss=0), None
            except Exception as e2:
                logger.error(f"Error generating thumbnail at 0s for {video_path}: {e2}")
                raise HTTPException(status_code=500, detail="Failed to generate thumbnail")

    def _generate_thumbnail(self, video_path: str, ss: float) -> bytes:
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
    
    def get_video_duration(self, video_path: str) -> float:
        """
        Get the duration of the video in seconds using ffprobe.
        """
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "format=duration",
            "-of", "json",
            video_path
        ]

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )

        data = json.loads(result.stdout)
        return float(data["format"]["duration"])

  
def get_thumbnail_resolver():
    return ThumbnailResolver()

ThumbnailResolverDep = Annotated[ThumbnailResolver, Depends(get_thumbnail_resolver)]