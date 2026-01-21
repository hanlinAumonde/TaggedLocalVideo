from typing import Optional
import strawberry

from src.schema.types.pydantic_types.fileBrowe_type import RelativePathInputModel
from src.schema.types.pydantic_types.batch_operation_type import (
    TagsOperationMappingInputModel,
    VideosBatchOperationInputModel
)
from src.schema.types.video_type import Video

@strawberry.type
class FileBrowseNode:
    node: Video

@strawberry.experimental.pydantic.input(model=RelativePathInputModel)
class RelativePathInput:
    # refreshFlag: bool = False  # If True, bypass any caching and get the latest info from disk
    relativePath: strawberry.auto
    parsedPath: strawberry.auto


@strawberry.experimental.pydantic.input(model=TagsOperationMappingInputModel)
class TagsOperationMappingInput:
    append: strawberry.auto
    tags: strawberry.auto


@strawberry.experimental.pydantic.input(model=VideosBatchOperationInputModel)
class VideosBatchOperationInput:
    videoIds: strawberry.auto
    tagsOperation: Optional[TagsOperationMappingInput] = None
    author: strawberry.auto

@strawberry.type
class VideosBatchOperationResult:
    success: bool
    successfulUpdatesMappings: list[strawberry.ID] 

@strawberry.type
class VideoMutationResult:
    success: bool
    video: Optional[Video] = None