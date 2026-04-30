from pathlib import Path
from src.db.models.Video_model import VideoModel
from src.services.resource_handler.absolute_path import AbsolutePath


# -----------------------------------------------------------------------
# ------------------- Root level listing ---------------------------------
# -----------------------------------------------------------------------

async def test_root_level_lists_categories(browse_svc, init_db):
    abs_path = AbsolutePath(abs_path=None, category=None, handler=None)
    nodes = await browse_svc.get_node_list_in_directory(abs_path)

    names = [n.node.name for n in nodes]
    assert "Test-category" in names
    assert all(n.node.isDir for n in nodes)


# -----------------------------------------------------------------------
# ------------------- Category level listing -----------------------------
# -----------------------------------------------------------------------

async def test_category_level_lists_pseudo_names(
    browse_svc, init_db, local_resource_handler_service, local_resource_dir,
):
    handler = local_resource_handler_service.get_handler("Test-category")
    abs_path = AbsolutePath.from_existing_path(
        path="Test-category", category="Test-category", handler=handler,
    )
    nodes = await browse_svc.get_node_list_in_directory(abs_path)

    names = [n.node.name for n in nodes]
    assert "Test-resource" in names


# -----------------------------------------------------------------------
# ------------------- Directory level listing ----------------------------
# -----------------------------------------------------------------------

async def test_directory_level_discovers_videos_and_subdirs(
    browse_svc, init_db, local_resource_handler_service, local_resource_dir,
):
    handler = local_resource_handler_service.get_handler("Test-category")
    root_fs = str(local_resource_dir).replace("\\", "/")
    abs_path = AbsolutePath.from_existing_path(
        path=root_fs, category="Test-category", handler=handler,
    )

    nodes = await browse_svc.get_node_list_in_directory(abs_path)
    names = [n.node.name for n in nodes]

    # Should find movie_a, movie_b (videos) and subdir (directory).
    # notes.txt is not a video, skipped. empty/ has 0 size → skipped.
    assert "movie_a" in names
    assert "movie_b" in names
    assert "subdir" in names
    assert "notes" not in names


async def test_directory_level_inserts_video_model_on_first_browse(
    browse_svc, init_db, local_resource_handler_service, local_resource_dir,
):
    handler = local_resource_handler_service.get_handler("Test-category")
    root_fs = str(local_resource_dir).replace("\\", "/")
    abs_path = AbsolutePath.from_existing_path(
        path=root_fs, category="Test-category", handler=handler,
    )

    await browse_svc.get_node_list_in_directory(abs_path)

    # Videos should now exist in the database.
    db_path = handler.convert_to_DB_format_path(
        str(local_resource_dir / "movie_a.mp4").replace("\\", "/")
    )
    video = await VideoModel.find_one({"path": db_path})
    assert video is not None
    assert video.name == "movie_a"
    assert video.size == 100.0
    assert video.category == "Test-category"


async def test_directory_level_does_not_duplicate_on_rebrowse(
    browse_svc, init_db, local_resource_handler_service, local_resource_dir,
):
    handler = local_resource_handler_service.get_handler("Test-category")
    root_fs = str(local_resource_dir).replace("\\", "/")
    abs_path = AbsolutePath.from_existing_path(
        path=root_fs, category="Test-category", handler=handler,
    )

    await browse_svc.get_node_list_in_directory(abs_path)
    await browse_svc.get_node_list_in_directory(abs_path)

    all_videos = await VideoModel.find({"category": "Test-category"}).to_list()
    paths = [v.path for v in all_videos]
    assert len(paths) == len(set(paths))  # no duplicates


# -----------------------------------------------------------------------
# ------------------- get_all_video_entries_in_directory ------------------
# -----------------------------------------------------------------------

def test_get_all_video_entries_recursive(
    browse_svc, local_resource_handler_service, local_resource_dir: Path,
):
    handler = local_resource_handler_service.get_handler("Test-category")
    root_fs = str(local_resource_dir).replace("\\", "/")

    entries = browse_svc.get_all_video_entries_in_directory(root_fs, "Test-category")
    names = sorted(e.name for e in entries)

    assert names == ["movie_a.mp4", "movie_b.mp4", "movie_c.mp4"]


def test_get_all_video_entries_empty_dir(
    browse_svc, local_resource_handler_service, local_resource_dir: Path,
):
    empty = str(local_resource_dir / "subdir" / "empty").replace("\\", "/")
    entries = browse_svc.get_all_video_entries_in_directory(empty, "Test-category")
    assert entries == []
