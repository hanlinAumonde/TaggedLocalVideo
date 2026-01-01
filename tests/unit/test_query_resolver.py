import pytest
from bson import ObjectId

from src.app import schema
from src.db.models.Video_model import VideoModel, VideoTagModel
from src.context import AppContext


@pytest.mark.unit
class TestResolveSearchVideos:
    """test resolve_search_videos function"""

    @pytest.mark.asyncio
    async def test_search_by_title_keyword(self, init_test_db, sample_videos, app_context):
        """test search by title keyword"""
        query = """
            query SearchVideos($input: VideoSearchInput!) {
                SearchVideos(input: $input) {
                    pagination {
                        size
                        totalCount
                        currentPageNumber
                    }
                    videos {
                        id
                        name
                    }
                }
            }
        """

        result = await schema.execute(
            query,
            variable_values={
                "input": {
                    "titleKeyword": {"keyWord": "popular"},
                    "author": {},
                    "tags": [],
                    "sortBy": "LATEST",
                    "fromPage": "SearchPage",
                    "currentPageNumber": 1
                }
            },
            context_value=app_context
        )

        assert result.errors is None
        assert result.data["SearchVideos"]["pagination"]["currentPageNumber"] == 1
        assert result.data["SearchVideos"]["pagination"]["totalCount"] >= 1
        assert len(result.data["SearchVideos"]["videos"]) >= 1
        assert "popular" in result.data["SearchVideos"]["videos"][0]["name"].lower()

    @pytest.mark.asyncio
    async def test_search_by_tags(self, init_test_db, sample_videos, app_context):
        """测试按标签搜索"""
        query = """
            query SearchVideos($input: VideoSearchInput!) {
                SearchVideos(input: $input) {
                    pagination {
                        totalCount
                    }
                    videos {
                        id
                        tags {
                            name
                        }
                    }
                }
            }
        """

        result = await schema.execute(
            query,
            variable_values={
                "input": {
                    "titleKeyword": {},
                    "author": {},
                    "tags": ["action"],
                    "sortBy": "LATEST",
                    "fromPage": "SearchPage",
                    "currentPageNumber": 1
                }
            },
            context_value=app_context
        )

        # 验证结果包含 action 标签
        assert result.errors is None
        assert result.data["SearchVideos"]["pagination"]["totalCount"] >= 1
        for video in result.data["SearchVideos"]["videos"]:
            tag_names = [tag["name"] for tag in video["tags"]]
            assert "action" in tag_names

    @pytest.mark.asyncio
    async def test_search_sort_by_most_viewed(self, init_test_db, sample_videos, app_context):
        """测试按观看次数排序"""
        query = """
            query SearchVideos($input: VideoSearchInput!) {
                SearchVideos(input: $input) {
                    videos {
                        id
                        viewCount
                    }
                }
            }
        """

        result = await schema.execute(
            query,
            variable_values={
                "input": {
                    "titleKeyword": {},
                    "author": {},
                    "tags": [],
                    "sortBy": "MOST_VIEWED",
                    "fromPage": "SearchPage",
                    "currentPageNumber": 1
                }
            },
            context_value=app_context
        )

        assert result.errors is None
        # 验证结果按观看次数降序排列
        videos = result.data["SearchVideos"]["videos"]
        if len(videos) > 1:
            for i in range(len(videos) - 1):
                assert videos[i]["viewCount"] >= videos[i + 1]["viewCount"]

    @pytest.mark.asyncio
    async def test_search_pagination(self, init_test_db, video_factory, app_context):
        """测试分页功能"""
        # 创建多个视频
        for i in range(20):
            await video_factory(
                path=f"/test/video_{i}.mp4",
                name=f"video_{i}.mp4"
            )

        query = """
            query SearchVideos($input: VideoSearchInput!) {
                SearchVideos(input: $input) {
                    pagination {
                        size
                        totalCount
                        currentPageNumber
                    }
                    videos {
                        id
                    }
                }
            }
        """

        result = await schema.execute(
            query,
            variable_values={
                "input": {
                    "titleKeyword": {},
                    "author": {},
                    "tags": [],
                    "sortBy": "LATEST",
                    "fromPage": "SearchPage",
                    "currentPageNumber": 2
                }
            },
            context_value=app_context
        )

        # 验证分页
        assert result.errors is None
        assert result.data["SearchVideos"]["pagination"]["currentPageNumber"] == 2
        assert result.data["SearchVideos"]["pagination"]["totalCount"] == 20
        assert result.data["SearchVideos"]["pagination"]["size"] == 15  # 搜索页默认每页15条


@pytest.mark.unit
class TestResolveGetTopTags:
    """测试 resolve_get_top_tags 函数"""

    @pytest.mark.asyncio
    async def test_get_top_tags(self, init_test_db, sample_tags, app_context):
        """测试获取热门标签"""
        query = """
            query GetTopTags {
                getTopTags {
                    name
                    count
                }
            }
        """

        result = await schema.execute(
            query,
            context_value=app_context
        )

        # 验证返回标签列表
        assert result.errors is None
        tags = result.data["getTopTags"]
        assert len(tags) > 0
        assert tags[0]["count"] >= tags[-1]["count"]  # 按使用次数降序

    @pytest.mark.asyncio
    async def test_top_tags_limit(self, init_test_db, tag_factory, app_context):
        """测试标签数量限制"""
        # 创建超过限制数量的标签
        for i in range(30):
            await tag_factory(
                name=f"tag_{i}",
                tag_count=30 - i
            )

        query = """
            query GetTopTags {
                getTopTags {
                    name
                    count
                }
            }
        """

        result = await schema.execute(
            query,
            context_value=app_context
        )

        # 验证返回数量不超过配置的限制
        assert result.errors is None
        tags = result.data["getTopTags"]
        assert len(tags) <= app_context.pagination_sizes["homepage_tags"]

    @pytest.mark.asyncio
    async def test_empty_tags(self, init_test_db, app_context):
        """测试没有标签时的情况"""
        query = """
            query GetTopTags {
                getTopTags {
                    name
                    count
                }
            }
        """

        result = await schema.execute(
            query,
            context_value=app_context
        )

        assert result.errors is None
        assert result.data["getTopTags"] == []


@pytest.mark.unit
class TestResolveGetSuggestions:
    """测试 resolve_get_suggestions 函数"""

    @pytest.mark.asyncio
    async def test_get_title_suggestions(self, init_test_db, sample_videos, app_context):
        """测试获取标题建议"""
        query = """
            query GetSuggestions($input: SuggestionInput!) {
                getSuggestions(input: $input)
            }
        """

        result = await schema.execute(
            query,
            variable_values={
                "input": {
                    "keyword": {"keyWord": "video"},
                    "suggestionType": "NAME"
                }
            },
            context_value=app_context
        )

        # 验证返回字符串列表
        assert result.errors is None
        suggestions = result.data["getSuggestions"]
        assert isinstance(suggestions, list)
        if len(suggestions) > 0:
            assert isinstance(suggestions[0], str)
            assert "video" in suggestions[0].lower()

    @pytest.mark.asyncio
    async def test_get_author_suggestions(self, init_test_db, sample_videos, app_context):
        """测试获取作者建议"""
        query = """
            query GetSuggestions($input: SuggestionInput!) {
                getSuggestions(input: $input)
            }
        """

        result = await schema.execute(
            query,
            variable_values={
                "input": {
                    "keyword": {"keyWord": "test"},
                    "suggestionType": "AUTHOR"
                }
            },
            context_value=app_context
        )

        assert result.errors is None
        suggestions = result.data["getSuggestions"]
        assert isinstance(suggestions, list)
        if len(suggestions) > 0:
            assert isinstance(suggestions[0], str)

    @pytest.mark.asyncio
    async def test_get_tag_suggestions(self, init_test_db, sample_tags, app_context):
        """测试获取标签建议"""
        query = """
            query GetSuggestions($input: SuggestionInput!) {
                getSuggestions(input: $input)
            }
        """

        result = await schema.execute(
            query,
            variable_values={
                "input": {
                    "keyword": {"keyWord": "act"},
                    "suggestionType": "TAG"
                }
            },
            context_value=app_context
        )

        # 标签建议返回字符串列表(根据schema定义)
        assert result.errors is None
        suggestions = result.data["getSuggestions"]
        assert isinstance(suggestions, list)


@pytest.mark.unit
class TestResolveGetVideoById:
    """测试 resolve_get_video_by_id 函数"""

    @pytest.mark.asyncio
    async def test_get_existing_video(self, init_test_db, sample_videos):
        """测试获取存在的视频"""
        video_id = str(sample_videos[0].id)

        query = """
            query GetVideoById($videoId: ID!) {
                getVideoById(videoId: $videoId) {
                    id
                    name
                }
            }
        """

        result = await schema.execute(
            query,
            variable_values={"videoId": video_id}
        )

        assert result.errors is None
        video = result.data["getVideoById"]
        assert video is not None
        assert video["id"] == video_id
        assert video["name"] == sample_videos[0].name

    @pytest.mark.asyncio
    async def test_get_nonexistent_video(self, init_test_db):
        """测试获取不存在的视频"""
        fake_id = str(ObjectId())

        query = """
            query GetVideoById($videoId: ID!) {
                getVideoById(videoId: $videoId) {
                    id
                }
            }
        """

        result = await schema.execute(
            query,
            variable_values={"videoId": fake_id}
        )

        # GraphQL 会捕获异常并返回在 errors 中
        assert result.errors is not None
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_get_video_with_invalid_id(self, init_test_db):
        """测试使用无效的视频 ID"""
        query = """
            query GetVideoById($videoId: ID!) {
                getVideoById(videoId: $videoId) {
                    id
                }
            }
        """

        result = await schema.execute(
            query,
            variable_values={"videoId": "invalid_id"}
        )

        # 应该抛出异常
        assert result.errors is not None
        assert len(result.errors) > 0


@pytest.mark.unit
class TestResolveBrowseDirectory:
    """测试 resolve_browse_directory 函数"""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="需要实现完整的文件浏览逻辑后再测试")
    async def test_browse_root_directory(self, init_test_db, app_context):
        """测试浏览根目录"""
        # 这个测试需要根据实际的 resolve_browse_directory 实现来编写
        pass

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="需要实现完整的文件浏览逻辑后再测试")
    async def test_browse_with_invalid_path(self, init_test_db, app_context):
        """测试使用无效路径浏览"""
        pass
