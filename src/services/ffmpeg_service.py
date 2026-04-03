import asyncio
from asyncio.subprocess import Process
import os
from functools import lru_cache
from typing import AsyncIterator

from src.config import get_settings
from src.logger import get_logger
from src.services.resource_handler.base_resource_handler import BaseResourceHandler

logger = get_logger("ffmpeg_service")


class FFmpegService:
    """Centralized service for all ffmpeg/ffprobe operations with shared concurrency control."""

    def __init__(self):
        self._semaphore = asyncio.Semaphore(
            max(
                get_settings().ffmpeg_semaphore_limit,
                os.cpu_count() // 2
            )
        )

    # --- Thumbnail generation ---

    async def generate_thumbnail(self, handler: BaseResourceHandler, fs_path: str) -> bytes:
        """
        Generate a JPEG thumbnail from video.
        Tries capturing at 10s first, falls back to 0s if video is too short.
        """
        async with self._semaphore:
            ffmpeg_input = handler.get_ffmpeg_accessible_path(fs_path)
            if ffmpeg_input:
                try:
                    return await self._run_thumbnail_command(ffmpeg_input, ss=10)
                except Exception as e:
                    logger.warning(f"Thumbnail at 10s failed for {fs_path}: {e}, retrying at 0s")
                    return await self._run_thumbnail_command(ffmpeg_input, ss=0)
            else:
                return await self._run_thumbnail_piped(handler, fs_path)

    @staticmethod
    async def _run_thumbnail_command(ffmpeg_input: str, ss: float) -> bytes:
        """Direct mode: -ss before -i for fast seeking."""
        process = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-loglevel", "error",
            "-ss", str(ss),
            "-i", ffmpeg_input,
            "-frames:v", "1",
            "-f", "image2",
            "-vcodec", "mjpeg",
            "-vf", "scale=320:-1",
            "pipe:1",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {stderr.decode(errors='replace')}")
        if not stdout:
            raise RuntimeError("ffmpeg produced no thumbnail data")
        return stdout

    async def _run_thumbnail_piped(self, handler: BaseResourceHandler, fs_path: str) -> bytes:
        """Pipe fallback: feed file via stdin. -ss must go after -i (no seeking on pipe)."""
        process = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-loglevel", "error",
            "-i", "pipe:0",
            "-ss", "10",
            "-frames:v", "1",
            "-f", "image2",
            "-vcodec", "mjpeg",
            "-vf", "scale=320:-1",
            "pipe:1",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await self._feed_stdin(handler, fs_path, process.stdin)
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"ffmpeg piped failed: {stderr.decode(errors='replace')}")
        if not stdout:
            raise RuntimeError("ffmpeg produced no thumbnail data")
        return stdout

    # --- Duration extraction ---

    async def get_video_duration(self, handler: BaseResourceHandler, fs_path: str) -> float:
        """Get video duration in seconds using ffprobe."""
        async with self._semaphore:
            try:
                ffmpeg_input = handler.get_ffmpeg_accessible_path(fs_path)
                if ffmpeg_input:
                    return await self._run_duration_command(ffmpeg_input)
                else:
                    return await self._run_duration_piped(handler, fs_path)
            except Exception as e:
                logger.warning(f"Failed to get duration for {fs_path}: {e}")
                return 0.0

    @staticmethod
    async def _run_duration_command(ffmpeg_input: str) -> float:
        process = await asyncio.create_subprocess_exec(
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            ffmpeg_input,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {stderr.decode(errors='replace')}")
        return float(stdout)

    async def _run_duration_piped(self, handler: BaseResourceHandler, fs_path: str) -> float:
        process = await asyncio.create_subprocess_exec(
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            "pipe:0",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await self._feed_stdin(handler, fs_path, process.stdin)
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"ffprobe piped failed: {stderr.decode(errors='replace')}")
        return float(stdout)

    # --- Live transcoding to MP4 ---

    async def transcode_to_mp4_stream(
        self, handler: BaseResourceHandler, fs_path: str
    ) -> AsyncIterator[bytes]:
        """
        Transcode video to fragmented MP4 on-the-fly.
        Returns an async iterator that yields 1MB chunks.
        The semaphore is held for the entire duration of the stream.
        """
        await self._semaphore.acquire()

        ffmpeg_input = handler.get_ffmpeg_accessible_path(fs_path)

        try:
            if ffmpeg_input:
                process = await asyncio.create_subprocess_exec(
                    "ffmpeg",
                    "-loglevel", "error",
                    "-i", ffmpeg_input,
                    "-c:v", "libx264",
                    "-preset", "fast",
                    "-crf", "23",
                    "-c:a", "aac",
                    "-movflags", "frag_keyframe+empty_moov+default_base_moof",
                    "-f", "mp4",
                    "pipe:1",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            else:
                process = await asyncio.create_subprocess_exec(
                    "ffmpeg",
                    "-loglevel", "error",
                    "-i", "pipe:0",
                    "-c:v", "libx264",
                    "-preset", "fast",
                    "-crf", "23",
                    "-c:a", "aac",
                    "-movflags", "frag_keyframe+empty_moov+default_base_moof",
                    "-f", "mp4",
                    "pipe:1",
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                # Feed stdin in background so stdout reading isn't blocked
                asyncio.create_task(self._feed_stdin(handler, fs_path, process.stdin))
        except Exception as e:
            self._semaphore.release()
            logger.exception(f"Failed to start ffmpeg transcoding: {e}")
            raise

        async for chunk in self._iter_process_output(process):
            yield chunk

    # --- Internal helpers ---

    async def _iter_process_output(self, process: Process):
        """Read stdout in 1MB chunks, clean up process and release semaphore when done."""
        try:
            while True:
                chunk = await process.stdout.read(1024 * 1024)
                if not chunk:
                    break
                yield chunk
            await process.wait()
            if process.returncode != 0:
                stderr_output = await process.stderr.read()
                logger.error(
                    f"ffmpeg transcoding failed (exit {process.returncode}): "
                    f"{stderr_output.decode(errors='replace')}"
                )
        except Exception as e:
            logger.error(f"Error during transcoding stream: {e}")
            if process.returncode is None:
                process.kill()
                await process.wait()
        finally:
            self._semaphore.release()

    @staticmethod
    async def _feed_stdin(
        handler: BaseResourceHandler, fs_path: str, stdin: asyncio.StreamWriter
    ):
        """Stream file content from handler into ffmpeg's stdin."""
        try:
            file_size = int(handler.get_size(fs_path))
            offset = 0
            chunk_size = 1024 * 1024
            while offset < file_size:
                length = min(chunk_size, file_size - offset)
                chunk = await handler.read_file_chunk(fs_path, offset, length)
                if not chunk:
                    break
                stdin.write(chunk)
                await stdin.drain()
                offset += len(chunk)
        except Exception as e:
            logger.error(f"Error feeding stdin for {fs_path}: {e}")
        finally:
            stdin.close()


@lru_cache()
def get_ffmpeg_service() -> FFmpegService:
    return FFmpegService()
