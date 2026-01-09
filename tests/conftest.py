from typing import AsyncGenerator, Callable
from src import config
from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
import pytest
import pytest_asyncio
from beanie import init_beanie
from httpx import AsyncClient, ASGITransport
from mongomock_motor import AsyncMongoMockClient
from strawberry.fastapi import GraphQLRouter

from src.app import schema
from src.config import Settings
from src.db.models.Video_model import VideoModel, VideoTagModel

# ============================================================================
# Test Config Fixtures
# ============================================================================

@pytest.fixture
def test_config() -> dict:
    return {
        "resource_paths": {
            "pseudo1": "/test/path1",
            "pseudo2": "/test/path2",
        },
        "page_size_default": {
            "homepage_videos": 5,
            "homepage_tags": 20,
            "searchpage": 15,
        },
        "suggestion_limit": {
            "name": 10,
            "author": 10,
            "tag": 20,
        },
        "video_extensions": [
            ".mp4", ".avi", ".mkv", ".mov",
            ".wmv", ".flv", ".webm", ".m4v"
        ],
        "mongo": {
            "host":"localhost",
            "port":"27017",
            "database": "test_video_tag_db"
        }
    }


@pytest.fixture
def test_settings(test_config: dict) -> Settings:
    """Create Settings instance from test config"""
    return Settings.model_validate(test_config)


@pytest.fixture(autouse=True)
def mock_get_settings(test_settings: Settings, monkeypatch):
    original = config.get_settings
    original.cache_clear()
    monkeypatch.setattr(config,"get_settings", lambda: test_settings)
    yield
    original.cache_clear()


# ============================================================================
# DB Fixtures (mongomock)
# ============================================================================

# Mongomock has no support for AsyncMongoClient of pymongo right now

@pytest_asyncio.fixture
async def mock_db() -> AsyncGenerator[AsyncMongoMockClient, None]:
    client = AsyncMongoMockClient()
    yield client
    client.close()


@pytest_asyncio.fixture
async def init_test_db(mock_db: AsyncMongoMockClient):
    database = mock_db.get_database("test_video_tag_db")

    await init_beanie(
        database=database,
        document_models=[VideoModel, VideoTagModel]
    )

    yield

    await VideoModel.delete_all()
    await VideoTagModel.delete_all()
    

# ============================================================================
# FastAPI async client Fixtures
# ============================================================================


# @pytest_asyncio.fixture
# async def async_client(
#     init_test_db,
# ):
#     @asynccontextmanager
#     async def lifespan(app: FastAPI):
#         yield

#     app = FastAPI(lifespan=lifespan)
#     graphql_app = GraphQLRouter(schema=schema)
#     app.include_router(graphql_app, prefix="/graphql")
    
#     transport = ASGITransport(app=app)
#     async with AsyncClient(transport=transport, base_url="http://test") as ac:
#         yield ac


# ============================================================================
# Test data factory Fixtures
# ============================================================================

@pytest_asyncio.fixture
def video_factory() -> Callable[..., AsyncGenerator[VideoModel, None]]:
    async def _create_video(**kwargs) -> VideoModel:
        default_data = {
            "path": f"/test/video_{id(kwargs)}.mp4",
            "name": "test_video.mp4",
            "isDir": False,
            "size": 1024000,
            "lastModifyTime": 1640000000.0,
            "tags": ["test"],
            "author": "Test Author",
            "introduction": "Test introduction",
            "loved": False,
            "viewCount": 0,
            "lastViewTime": 0.0,
        }
        default_data.update(kwargs)
        video = VideoModel(**default_data)
        await video.insert()
        return video

    return _create_video

@pytest_asyncio.fixture
def tag_factory() -> Callable[..., AsyncGenerator[VideoTagModel, None]]:
    async def _create_tag(**kwargs) -> VideoTagModel:
        default_data = {
            "name": f"tag_{id(kwargs)}",
            "tag_count": 1,
        }
        default_data.update(kwargs)
        tag = VideoTagModel(**default_data)
        await tag.insert()
        return tag

    return _create_tag


@pytest_asyncio.fixture
async def sample_videos(init_test_db, video_factory):
    return [
        await video_factory(
            path="/test/video1.mp4",
            name="loved_video.mp4",
            loved=True,
            viewCount=100,
            lastViewTime=1640000000.0,
            tags=["action", "thriller"],
        ),
        await video_factory(
            path="/test/video2.mp4",
            name="popular_video.mp4",
            viewCount=500,
            lastModifyTime=1640100000.0,
            tags=["comedy", "action"],
        ),
        await video_factory(
            path="/test/video3.mp4",
            name="new_video.mp4",
            lastModifyTime=1640200000.0,
            tags=["drama"],
        ),
    ]


@pytest_asyncio.fixture
async def sample_tags(init_test_db, tag_factory):
    return [
        await tag_factory(name="action", tag_count=2),
        await tag_factory(name="comedy", tag_count=1),
        await tag_factory(name="drama", tag_count=1),
        await tag_factory(name="thriller", tag_count=1),
    ]
