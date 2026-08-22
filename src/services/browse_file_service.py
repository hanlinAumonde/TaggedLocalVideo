import strawberry
from bson import ObjectId

from src.config import Settings
from src.db.models.Video_model import VideoModel
from src.errors import FileBrowseError
from src.logger import get_logger
from src.services.dir_metadata_service import DirMetadataService
from src.services.resource_handler.absolute_path import AbsolutePath
from src.services.resource_handler.base_file_entry import BaseFileEntry
from src.services.resource_handler.resource_handler_service import ResourceHandlerService
from src.schema.types.fileBrowse_type import FileBrowseNode
from src.schema.types.video_type import Video
from src.services.tasks.migration_service import find_locked_paths

logger = get_logger("browse_file_service")

class BrowseFileService:
    def __init__(
        self,
        settings: Settings,
        dir_metadata_service: DirMetadataService,
        resource_handler_service: ResourceHandlerService,
    ):
        self.settings = settings
        self.dirMetadataService = dir_metadata_service
        self.resourceHandlerService = resource_handler_service

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
                    await self._get_directory_node(
                        AbsolutePath.from_relative_path(
                            parsedPath=(category, name, None), 
                            handlerService=self.resourceHandlerService,
                            settings=self.settings
                        ),
                        name,
                        fileBrowse_nodes,
                        skipCache,
                        recursiveCalculation
                    )
            else:
                category = abs_path.category
                handler = self.resourceHandlerService.get_handler(category)
                # (node, DB path) for each file, so one bulk lock lookup can mark them all
                # once the walk is done.
                file_nodes: list[tuple[FileBrowseNode, str]] = []
                with handler.list_directory(abs_path.FS_format_path()) as entries:
                    hasNewFileFlag = False
                    for entry in entries:
                        try:
                            entry_path = AbsolutePath.from_existing_path(
                                path=entry.path, 
                                category=category, 
                                handler=handler
                            )
                            if entry.is_dir():
                                await self._get_directory_node(
                                    entry_path,
                                    entry.name,
                                    fileBrowse_nodes,
                                    skipCache,
                                    recursiveCalculation
                                )
                            elif entry.is_file() and handler.is_video_file(entry.name):
                                stat = entry.stat()
                                if not hasNewFileFlag:
                                    hasNewFileFlag = await VideoModel.find_one(
                                        {"path": entry_path.DB_format_path()}
                                    ) is None
                                video_doc = await VideoModel.get_pymongo_collection().find_one_and_update(
                                    {"path": entry_path.DB_format_path()},
                                    {"$setOnInsert": VideoModel(
                                        category=category,
                                        path=entry_path.DB_format_path(),
                                        name=handler.get_filename_without_extension(entry.name),
                                        isDir=False,
                                        lastModifyTime=stat.mtime,
                                        size=stat.size,
                                        tags=[]
                                    ).model_dump()},
                                    upsert=True, return_document=True
                                )

                                file_node = FileBrowseNode(
                                    node=await Video.from_mongoDB(VideoModel(**video_doc), getTagsCount=False)
                                )
                                fileBrowse_nodes.append(file_node)
                                file_nodes.append((file_node, entry_path.DB_format_path()))
                        except OSError as e:
                            logger.exception(f"Error processing file {entry.path}: {e}")
                            continue

                    if hasNewFileFlag:
                        await self.dirMetadataService.update_directory_metadata_forward(abs_path)

                # Mark files held by a migration so the browser can disable them.
                if file_nodes:
                    locked_paths = await find_locked_paths(path for _, path in file_nodes)
                    for file_node, path in file_nodes:
                        file_node.node.isLocked = path in locked_paths

        except (OSError, Exception) as e:
            logger.exception(f"Error accessing directory {abs_path}: {e}")
            raise FileBrowseError(f"Error accessing directory {abs_path}")

        return fileBrowse_nodes

    async def _get_directory_node(self,
                                  path: AbsolutePath,
                                  name: str,
                                  fileBrowse_nodes: list[FileBrowseNode],
                                  skipCache: bool,
                                  recursiveCalculation: bool) -> None:
        """
        Helper method to get a FileBrowseNode for a directory, calculating its metadata and adding it to the list.

        :param path: The absolute path of the directory.
        :type path: AbsolutePath
        :param name: The name of the directory.
        :type name: str
        :param fileBrowse_nodes: The list to which the resulting FileBrowseNode will be added.
        :type fileBrowse_nodes: list[FileBrowseNode]
        :param skipCache: Whether to skip cache when calculating directory metadata.
        :type skipCache: bool
        :param recursiveCalculation: Whether to calculate directory metadata recursively.
        :type recursiveCalculation: bool    
        """
        total_size, last_modified_time = await self.dirMetadataService.calculate_directory_metadata(
            directory_path=path,
            skipCache=skipCache,
            recursiveCalculation=recursiveCalculation
        )
        if total_size != 0.0 and last_modified_time != 0.0:
            fileBrowse_nodes.append(
                FileBrowseNode(
                    node=Video.create_new(
                        id=strawberry.ID(str(ObjectId())),
                        name=name,
                        isDir=True,
                        lastModifyTime=last_modified_time,
                        size=total_size
                    )
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