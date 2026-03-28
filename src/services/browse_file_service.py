from functools import lru_cache
from bson import ObjectId
import strawberry
from src.config import get_settings
from src.db.models.Video_model import VideoModel
from src.errors import FileBrowseError
from src.logger import get_logger
from src.services.dir_metadata_service import get_dir_metadata_service
from src.services.path_convert_service import AbsolutePath
from src.services.resource_handler.base_file_entry import BaseFileEntry
from src.services.resource_handler.resource_handler_service import get_resource_handler_service
from src.schema.types.fileBrowse_type import FileBrowseNode
from src.schema.types.video_type import Video

logger = get_logger("browse_file_service")

class BrowseFileService:
    def __init__(self):
        self.settings = get_settings()
        self.dirMetadataService = get_dir_metadata_service()
        self.resourceHandlerService = get_resource_handler_service()

    async def get_node_list_in_directory(self,
                                         abs_path: AbsolutePath,
                                         skipCache: bool = False,
                                         recursiveCalculation: bool = True
                                         ) -> list[FileBrowseNode]:
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
                        AbsolutePath.from_relative_path((category, name, None)),
                        name,
                        fileBrowse_nodes,
                        skipCache,
                        recursiveCalculation
                    )
            else:
                category = abs_path.category
                handler = self.resourceHandlerService.get_handler(category)
                with handler.list_directory(abs_path.FS_format_path()) as entries:
                    hasNewFileFlag = False
                    for entry in entries:
                        try:
                            entry_path = AbsolutePath.from_existing_path(entry.path, category)
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

                                fileBrowse_nodes.append(
                                    FileBrowseNode(
                                        node=await Video.from_mongoDB(VideoModel(**video_doc), getTagsCount=False)
                                    )
                                )
                        except OSError as e:
                            logger.exception(f"Error processing file {entry.path}: {e}")
                            continue

                    if hasNewFileFlag:
                        await self.dirMetadataService.update_directory_metadata_forward(abs_path)

        except (OSError, Exception) as e:
            logger.exception(f"Error accessing directory {abs_path}: {e}")
            raise FileBrowseError(f"Error accessing directory {abs_path}")

        return fileBrowse_nodes

    async def _get_directory_node(self,
                                  path: AbsolutePath,
                                  name: str,
                                  fileBrowse_nodes: list[FileBrowseNode],
                                  skipCache: bool,
                                  recursiveCalculation: bool):
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
        """Get all video file entries under the given directory and its subdirectories."""
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

@lru_cache
def get_browse_file_service() -> BrowseFileService:
    return BrowseFileService()
