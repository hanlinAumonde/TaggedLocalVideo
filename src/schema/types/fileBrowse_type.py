from enum import Enum
from typing import Optional
import strawberry

from src.schema.types.pydantic_types.fileBrowe_type import RelativePathInputModel
from src.schema.types.pydantic_types.batch_operation_type import (
    SeriesOperationInputModel,
    SeriesOrderEntryInputModel,
    TagsOperationMappingInputModel,
    VideosBatchOperationInputModel
)
from src.schema.types.video_type import Video

@strawberry.enum
class BatchResultType(Enum):
    Success = "Success"
    PartialSuccess = "PartialSuccess"
    Failure = "Failure"
    AlreadyUpToDate = "AlreadyUpToDate"

@strawberry.type
class FileBrowseNode:
    node: Video

@strawberry.experimental.pydantic.input(model=RelativePathInputModel)
class RelativePathInput:
    skipCache: strawberry.auto
    recursiveCalculation: strawberry.auto
    relativePath: strawberry.auto
    parsedPath: strawberry.auto


@strawberry.experimental.pydantic.input(model=TagsOperationMappingInputModel)
class TagsOperationMappingInput:
    append: strawberry.auto
    tags: strawberry.auto


@strawberry.experimental.pydantic.input(model=SeriesOrderEntryInputModel)
class SeriesOrderEntryInput:
    videoId: strawberry.auto
    order: strawberry.auto


@strawberry.experimental.pydantic.input(model=SeriesOperationInputModel)
class SeriesOperationInput:
    name: strawberry.auto
    clear: strawberry.auto
    orders: list[SeriesOrderEntryInput] = strawberry.field(default_factory=list)


@strawberry.experimental.pydantic.input(model=VideosBatchOperationInputModel)
class VideosBatchOperationInput:
    videoIds: strawberry.auto
    relativePath: RelativePathInput
    tagsOperation: Optional[TagsOperationMappingInput] = None
    author: strawberry.auto
    seriesOperation: Optional[SeriesOperationInput] = None

@strawberry.type
class VideosBatchOperationResult:
    resultType: BatchResultType
    message: Optional[str] = None

@strawberry.type
class BatchOperationStatus:
    result: Optional[VideosBatchOperationResult]
    status: Optional[str] = None

@strawberry.type
class VideoMutationResult:
    success: bool
    video: Optional[Video] = None