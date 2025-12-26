from typing import Optional
import strawberry

from src.schema.types.video_type import Video


@strawberry.type
class FileBrowseNode:
    node: Video

@strawberry.input
class RelativePathInput:
    relativePath: Optional[str] = None  # If None, browse the root directory that contains all resources paths with their pesudo names

@strawberry.input
class TagsOperationBatchInput:
    append: bool # True for append, False for remove
    mapping: dict[strawberry.ID, list[str]] # videoId to list of tags

@strawberry.type
class TagsOperationBatchResult:
    success: bool
    successfulUpdatesMapping: dict[strawberry.ID, list[str]]  # videoId to list of successfully updated tags

@strawberry.type
class VideoMutationResult:
    success: bool
    video: Optional[Video] = None