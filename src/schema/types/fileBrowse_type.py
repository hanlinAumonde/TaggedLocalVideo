from typing import Optional
import strawberry

from src.schema.types.pydantic_types.fileBrowe_type import RelativePathInputModel
from src.schema.types.video_type import Video

@strawberry.type
class FileBrowseNode:
    node: Video

@strawberry.experimental.pydantic.input(model=RelativePathInputModel)
class RelativePathInput:
    # refreshFlag: bool = False  # If True, bypass any caching and get the latest info from disk
    relativePath: strawberry.auto
    parsedPath: strawberry.auto

@strawberry.input
class TagsOperationMappingInput:
    append: bool # True for append, False for remove
    tags: list[str]

@strawberry.input
class VideosBatchOperationInput:
    videoIds: list[strawberry.ID] # list of videoId
    tagsOperation: Optional[TagsOperationMappingInput] = None
    author: Optional[str] = None # New author to set

@strawberry.type
class VideosBatchOperationResult:
    success: bool
    successfulUpdatesMappings: list[strawberry.ID] 

@strawberry.type
class VideoMutationResult:
    success: bool
    video: Optional[Video] = None