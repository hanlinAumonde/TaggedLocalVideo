"""Tests for the ``getDirectoryMetadata`` query."""

import pytest

from tests.graphql.helpers import (
    GET_DIRECTORY_METADATA,
    assert_error_contains,
    assert_no_errors,
    make_relative_path_input,
)


pytestmark = pytest.mark.query


async def test_directory_metadata_root_returns_zero(execute_gql, init_db):
    result = await execute_gql(
        GET_DIRECTORY_METADATA, {"input": make_relative_path_input(None)}
    )
    assert_no_errors(result)
    payload = result.data["getDirectoryMetadata"]
    assert payload == {"totalSize": 0.0, "lastModifiedTime": 0.0}


async def test_directory_metadata_category_returns_zero(execute_gql, init_db):
    result = await execute_gql(
        GET_DIRECTORY_METADATA,
        {"input": make_relative_path_input("Test-category")},
    )
    assert_no_errors(result)
    assert result.data["getDirectoryMetadata"] == {
        "totalSize": 0.0,
        "lastModifiedTime": 0.0,
    }


async def test_directory_metadata_uses_service(
    execute_gql, mock_dir_metadata_service, init_db
):
    mock_dir_metadata_service.calculate_directory_metadata.return_value = (
        2048.0,
        1700001234.0,
    )

    result = await execute_gql(
        GET_DIRECTORY_METADATA,
        {"input": make_relative_path_input("Test-category/Test-resource")},
    )

    assert_no_errors(result)
    payload = result.data["getDirectoryMetadata"]
    assert payload["totalSize"] == 2048.0
    assert payload["lastModifiedTime"] == 1700001234.0
    mock_dir_metadata_service.calculate_directory_metadata.assert_awaited_once()


async def test_directory_metadata_invalid_path(execute_gql, init_db):
    result = await execute_gql(
        GET_DIRECTORY_METADATA,
        {"input": make_relative_path_input("non-existent-cat")},
    )
    assert_error_contains(result, "RelativePathInput")
