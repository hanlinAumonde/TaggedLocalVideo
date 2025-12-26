from enum import Enum
import strawberry
from src.schema.types.fileBrowse_type import FileBrowseNode, RelativePathInput
from src.schema.types.search_type import SuggestionInput, SuggestionResults, VideoSearchInput, VideoSearchResult
from src.schema.types.video_type import Video, VideoTag



async def resolve_search_videos(input: VideoSearchInput, context: strawberry.Info) -> VideoSearchResult:
    """
    Resolve function to search for videos based on various criteria.
    
    :param input: Filter criteria for searching videos.
    :type input: VideoSearchInput
    :param context: GraphQL context information.
    :type context: strawberry.Info
    :return: Search results for videos.
    :rtype: VideoSearchResult
    """
    pass

async def resolve_get_top_tags(limit: int, context: strawberry.Info) -> list[VideoTag]:
    """
    Resolve function to retrieve the top video tags.
    
    :param context: GraphQL context information.
    :type context: strawberry.Info
    :return: List of top video tags.
    :rtype: list[VideoTag]
    """
    pass

async def resolve_get_suggestions(input: SuggestionInput, context: strawberry.Info) -> SuggestionResults:
    """
    Resolve function to get suggestions based on a keyword and suggestion type.

    :param input: Input containing the keyword and suggestion type.
    :type input: SuggestionInput
    :param context: GraphQL context information.
    :type context: strawberry.Info
    :return: Suggestion results.
    :rtype: SuggestionResults
    """
    pass

async def resolve_get_video_by_id(videoId: strawberry.ID) -> Video:
    """
    Resolve function to retrieve a video by its ID.

    :param videoId: The ID of the video to retrieve.
    :type videoId: strawberry.ID
    :return: The video corresponding to the given ID.
    :rtype: Video
    """
    pass

async def resolve_browse_directory(path: RelativePathInput, context: strawberry.Info) -> list[FileBrowseNode]:
    """
    Resolve function to browse videos in a directory specified by a relative path.
    
    :param path: The relative path to browse.
    :type path: RelativePathInput
    :param context: GraphQL context information.
    :type context: strawberry.Info
    :return: List of file browse nodes in the specified directory.
    :rtype: list[FileBrowseNode]
    """
    # 1. Resolve the absolute path from the relative path
        # Attention: If the path is empty, it means browsing the root directories provided by the configuration
    # 2. Query the file system to get the list of files(only videos) and directories in the specified path
    # 3. Convert the file system entries to FileBrowseNode instances
        # Atthention:
        # 1. For video files, we should check if they are in the database to get their metadata by using their absolute paths, if not, create a new Video instance with basic info 
        # 2. For directories, get its total size and the last modified time of all videos under it
    # 4. Return the list of FileBrowseNode instances


    pass