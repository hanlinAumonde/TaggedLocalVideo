import asyncio
from dataclasses import dataclass

import strawberry
from bson import ObjectId
from pymongo import UpdateOne

from src.config import Settings
from src.db.models.Video_model import VideoModel
from src.errors import FileBrowseError
from src.logger import get_logger
from src.services.dir_metadata_service import DirMetadataService
from src.services.ffmpeg_service import FFmpegService
from src.services.resource_handler.absolute_path import AbsolutePath
from src.services.resource_handler.base_file_entry import BaseFileEntry
from src.services.resource_handler.base_resource_handler import BaseResourceHandler
from src.services.resource_handler.resource_handler_service import ResourceHandlerService
from src.schema.types.fileBrowse_type import FileBrowseNode
from src.schema.types.video_type import Video
from src.services.tasks.migration_service import find_locked_paths

logger = get_logger("browse_file_service")


@dataclass(slots=True)
class _PendingVideo:
    """A video file seen while walking a directory, awaiting its database document."""
    db_path: str
    fs_path: str
    name: str
    mtime: float
    size: float


class BrowseFileService:
    def __init__(
        self,
        settings: Settings,
        dir_metadata_service: DirMetadataService,
        resource_handler_service: ResourceHandlerService,
        ffmpegService: FFmpegService
    ):
        self.settings = settings
        self.dirMetadataService = dir_metadata_service
        self.resourceHandlerService = resource_handler_service
        self.ffmpegService = ffmpegService

    async def get_node_list_in_directory(self,
                                         abs_path: AbsolutePath,
                                         skipCache: bool = False,
                                         recursiveCalculation: bool = True
                                         ) -> list[FileBrowseNode]:
        """
        Get a list of FileBrowseNode objects representing the files and directories under the specified absolute path.
        
        :param abs_path: The absolute path for which to retrieve the file and directory nodes.
        :type abs_path: AbsolutePath
        :param skipCache: Whether to skip cache when calculating directory metadata. Default is False.
        :type skipCache: bool
        :param recursiveCalculation: Whether to calculate directory metadata recursively. Default is True.
        :type recursiveCalculation: bool
        :return: A list of FileBrowseNode objects representing the files and directories under the specified absolute path.
        :rtype: list[FileBrowseNode]
        """
        fileBrowse_nodes: list[FileBrowseNode] = []
        try:
            if abs_path.is_root_level():
                for category in self.resourceHandlerService.get_all_categories():
                    fileBrowse_nodes.append(
                        FileBrowseNode(
                            node=Video.create_new(
                                id=strawberry.ID(str(ObjectId())),
                                name=category,
                                isDir=True,
                                lastModifyTime=0.0,
                                size=0.0
                            )
                        )
                    )
            elif abs_path.is_category_level():
                category = abs_path.category
                pseudo_names = self.resourceHandlerService.get_pseudo_names(category)
                for name in pseudo_names:
                    node = await self._get_directory_node(
                        AbsolutePath.from_relative_path(
                            parsedPath=(category, name, None),
                            handlerService=self.resourceHandlerService,
                            settings=self.settings
                        ),
                        name,
                        skipCache,
                        recursiveCalculation
                    )
                    if node is not None:
                        fileBrowse_nodes.append(node)
            else:
                fileBrowse_nodes = await self._list_directory_level(
                    abs_path, skipCache, recursiveCalculation
                )

        except (OSError, Exception) as e:
            logger.exception(f"Error accessing directory {abs_path}: {e}")
            raise FileBrowseError(f"Error accessing directory {abs_path}")

        return fileBrowse_nodes

    async def _list_directory_level(self,
                                    abs_path: AbsolutePath,
                                    skipCache: bool,
                                    recursiveCalculation: bool) -> list[FileBrowseNode]:
        """
        List a concrete directory: its sub-directories plus every video file it holds.

        Sub-directories need no database work and are resolved during the walk. Video
        files only get collected, then resolved as a single batch, so a directory holding
        a hundred videos costs a handful of round-trips instead of a few hundred — see
        ``_sync_video_documents``. Directories therefore lead the returned list; the
        frontend sorts the whole listing itself, so the grouping is not user-visible.

        :param abs_path: The absolute path of the directory to list.
        :type abs_path: AbsolutePath
        :param skipCache: Whether to skip cache when calculating directory metadata.
        :type skipCache: bool
        :param recursiveCalculation: Whether to calculate directory metadata recursively.
        :type recursiveCalculation: bool
        :return: The nodes of the directory: sub-directories first, then video files.
        :rtype: list[FileBrowseNode]
        """
        category = abs_path.category
        handler = self.resourceHandlerService.get_handler(category)

        directory_nodes: list[FileBrowseNode] = []
        pending: list[_PendingVideo] = []

        with handler.list_directory(abs_path.FS_format_path()) as entries:
            for entry in entries:
                try:
                    entry_path = AbsolutePath.from_existing_path(
                        path=entry.path,
                        category=category,
                        handler=handler
                    )
                    if entry.is_dir():
                        node = await self._get_directory_node(
                            entry_path, entry.name, skipCache, recursiveCalculation
                        )
                        if node is not None:
                            directory_nodes.append(node)
                    elif entry.is_file() and handler.is_video_file(entry.name):
                        stat = entry.stat()
                        pending.append(
                            _PendingVideo(
                                db_path=entry_path.DB_format_path(),
                                fs_path=entry.path,
                                name=handler.get_filename_without_extension(entry.name),
                                mtime=stat.mtime,
                                size=stat.size
                            )
                        )
                except OSError as e:
                    logger.exception(f"Error processing file {entry.path}: {e}")
                    continue

        if not pending:
            return directory_nodes

        documents, has_new_file = await self._sync_video_documents(handler, category, pending)

        # Files held by a migration are disabled in the browser: one lookup for all of them.
        locked_paths = await find_locked_paths(item.db_path for item in pending)
        video_nodes = [
            FileBrowseNode(
                node=await Video.from_mongoDB(
                    document,
                    getTagsCount=False,
                    isLocked=item.db_path in locked_paths
                )
            )
            for item in pending
            if (document := documents.get(item.db_path)) is not None
        ]

        if has_new_file:
            await self.dirMetadataService.update_directory_metadata_forward(abs_path)

        return directory_nodes + video_nodes

    async def _sync_video_documents(self,
                                    handler: BaseResourceHandler,
                                    category: str,
                                    pending: list[_PendingVideo]) -> tuple[dict[str, VideoModel], bool]:
        """
        Resolve the database document of every video file found in one directory,
        inserting the ones that are new and filling in the durations that are missing.

        The whole directory costs one ``find``, at most one ``bulk_write``, and — only
        when new files were discovered — one further ``find`` to read the inserted
        documents back. ffprobe is the expensive part of this method, so it runs only
        for documents that actually lack a duration; those probes run concurrently and
        FFmpegService's own semaphore caps how many really overlap.

        :param handler: The resource handler owning the directory being listed.
        :type handler: BaseResourceHandler
        :param category: The category the directory belongs to.
        :type category: str
        :param pending: The video files found while walking the directory.
        :type pending: list[_PendingVideo]
        :return: The document of each video keyed by DB path, and whether any file was new.
        :rtype: tuple[dict[str, VideoModel], bool]
        """
        documents = {
            document.path: document
            for document in await VideoModel.find(
                {"path": {"$in": [item.db_path for item in pending]}}
            ).to_list()
        }

        # Newly discovered files, plus known ones whose duration was never resolved.
        needs_duration = [
            item for item in pending
            if not (document := documents.get(item.db_path)) or not document.duration
        ]
        durations = dict(
            zip(
                (item.db_path for item in needs_duration),
                await asyncio.gather(*(
                    self.ffmpegService.get_video_duration(handler=handler, fs_path=item.fs_path)
                    for item in needs_duration
                ))
            )
        )

        operations: list[UpdateOne] = []
        inserted_paths: list[str] = []
        for item in pending:
            document = documents.get(item.db_path)
            if document is None:
                inserted_paths.append(item.db_path)
                new_document = VideoModel(
                    category=category,
                    path=item.db_path,
                    name=item.name,
                    isDir=False,
                    lastModifyTime=item.mtime,
                    size=item.size,
                    tags=[],
                    duration=durations.get(item.db_path, 0.0)
                )
                operations.append(
                    UpdateOne(
                        {"path": item.db_path},
                        {"$setOnInsert": new_document.model_dump(by_alias=True, exclude={"id"})},
                        upsert=True
                    )
                )
            elif item.db_path in durations:
                document.duration = durations[item.db_path]
                operations.append(
                    UpdateOne({"_id": document.id}, {"$set": {"duration": document.duration}})
                )

        if operations:
            await VideoModel.get_pymongo_collection().bulk_write(operations, ordered=False)

        if inserted_paths:
            # Read back instead of trusting the locally built model
            for document in await VideoModel.find({"path": {"$in": inserted_paths}}).to_list():
                documents[document.path] = document

        return documents, bool(inserted_paths)

    async def _get_directory_node(self,
                                  path: AbsolutePath,
                                  name: str,
                                  skipCache: bool,
                                  recursiveCalculation: bool) -> FileBrowseNode | None:
        """
        Helper method to build a FileBrowseNode for a directory from its calculated metadata.

        :param path: The absolute path of the directory.
        :type path: AbsolutePath
        :param name: The name of the directory.
        :type name: str
        :param skipCache: Whether to skip cache when calculating directory metadata.
        :type skipCache: bool
        :param recursiveCalculation: Whether to calculate directory metadata recursively.
        :type recursiveCalculation: bool
        :return: The node for the directory, or None if it holds nothing worth showing.
        :rtype: FileBrowseNode | None
        """
        total_size, last_modified_time = await self.dirMetadataService.calculate_directory_metadata(
            directory_path=path,
            skipCache=skipCache,
            recursiveCalculation=recursiveCalculation
        )
        if total_size == 0.0 or last_modified_time == 0.0:
            return None
        return FileBrowseNode(
            node=Video.create_new(
                id=strawberry.ID(str(ObjectId())),
                name=name,
                isDir=True,
                lastModifyTime=last_modified_time,
                size=total_size
            )
        )

    def get_all_video_entries_in_directory(self, mounted_directory_path: str, category: str) -> list[BaseFileEntry]:
        """
        Get all video file entries under the given directory and its subdirectories.

        :param mounted_directory_path: The path of the mounted directory.
        :type mounted_directory_path: str
        :param category: The category of the video files.
        :type category: str
        :return: A list of video file entries.
        :rtype: list[BaseFileEntry]
        """
        video_entries: list[BaseFileEntry] = []
        handler = self.resourceHandlerService.get_handler(category)
        try:
            with handler.list_directory(mounted_directory_path) as entries:
                for entry in entries:
                    if entry.is_file() and handler.is_video_file(entry.name):
                        video_entries.append(entry)
                    elif entry.is_dir():
                        video_entries.extend(
                            self.get_all_video_entries_in_directory(
                                handler.get_path_standard_format(entry.path),
                                category
                            )
                        )
        except (OSError, Exception):
            logger.exception(f"Error accessing directory {mounted_directory_path} to get video entries.")
        return video_entries