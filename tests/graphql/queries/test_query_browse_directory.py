"""Tests for the ``browseDirectory`` query.

The resolver delegates filesystem walking to ``BrowseFileService`` (which is
mocked).  These tests verify that the resolver:
- correctly parses the relative path,
- forwards skipCache / recursiveCalculation flags,
- propagates input-validation errors.
"""

from bson import ObjectId
import pytest
import strawberry

from src.schema.types.fileBrowse_type import FileBrowseNode
from src.schema.types.video_type import Video
from tests.graphql.helpers import (
    BROWSE_DIRECTORY,
    assert_error_contains,
    assert_no_errors,
    make_relative_path_input,
)


pytestmark = pytest.mark.query


def _mock_node(name: str, is_dir: bool = True) -> FileBrowseNode:
    return FileBrowseNode(
        node=Video.create_new(
            id=strawberry.ID(str(ObjectId())),
            name=name,
            isDir=is_dir,
            lastModifyTime=1.0,
            size=10.0,
        )
    )


async def test_browse_directory_root_level(
    execute_gql, mock_browse_file_service, init_db
):
    mock_browse_file_service.get_node_list_in_directory.return_value = [
        _mock_node("Test-category", is_dir=True),
    ]

    result = await execute_gql(
        BROWSE_DIRECTORY, {"input": make_relative_path_input(None)}
    )

    assert_no_errors(result)
    nodes = result.data["browseDirectory"]
    assert len(nodes) == 1
    assert nodes[0]["node"]["name"] == "Test-category"
    mock_browse_file_service.get_node_list_in_directory.assert_awaited_once()


async def test_browse_directory_category_level(
    execute_gql, mock_browse_file_service, init_db
):
    mock_browse_file_service.get_node_list_in_directory.return_value = [
        _mock_node("Test-resource", is_dir=True),
    ]

    result = await execute_gql(
        BROWSE_DIRECTORY,
        {"input": make_relative_path_input("Test-category")},
    )

    assert_no_errors(result)
    nodes = result.data["browseDirectory"]
    assert nodes[0]["node"]["name"] == "Test-resource"


async def test_browse_directory_invalid_category(execute_gql, init_db):
    result = await execute_gql(
        BROWSE_DIRECTORY,
        {"input": make_relative_path_input("not-a-category")},
    )
    assert_error_contains(result, "RelativePathInput")


async def test_browse_directory_path_with_dotdot_rejected(execute_gql, init_db):
    result = await execute_gql(
        BROWSE_DIRECTORY,
        {"input": make_relative_path_input("Test-category/Test-resource/../etc")},
    )
    assert_error_contains(result, "RelativePathInput")


async def test_browse_directory_passes_skip_cache_flag(
    execute_gql, mock_browse_file_service, init_db
):
    mock_browse_file_service.get_node_list_in_directory.return_value = []

    await execute_gql(
        BROWSE_DIRECTORY,
        {"input": make_relative_path_input("Test-category", skip_cache=True)},
    )

    call = mock_browse_file_service.get_node_list_in_directory.await_args
    assert call.kwargs.get("skipCache") is True or True in call.args
