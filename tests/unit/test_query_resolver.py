import pytest
from bson import ObjectId

from src.app import schema


@pytest.mark.unit
class TestResolveSearchVideos:

    @pytest.mark.asyncio
    async def test_search_by_title_keyword(self, init_test_db, sample_videos):
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
            }
        )

        assert result.errors is None
        assert result.data["SearchVideos"]["pagination"]["currentPageNumber"] == 1
        assert result.data["SearchVideos"]["pagination"]["totalCount"] >= 1
        assert len(result.data["SearchVideos"]["videos"]) >= 1
        assert "popular" in result.data["SearchVideos"]["videos"][0]["name"].lower()

    @pytest.mark.asyncio
    async def test_search_by_tags(self, init_test_db, sample_videos):
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
        )

        assert result.errors is None
        assert result.data["SearchVideos"]["pagination"]["totalCount"] >= 1
        for video in result.data["SearchVideos"]["videos"]:
            tag_names = [tag["name"] for tag in video["tags"]]
            assert "action" in tag_names

    @pytest.mark.asyncio
    async def test_search_sort_by_most_viewed(self, init_test_db, sample_videos):
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
        )

        assert result.errors is None
        videos = result.data["SearchVideos"]["videos"]
        if len(videos) > 1:
            for i in range(len(videos) - 1):
                assert videos[i]["viewCount"] >= videos[i + 1]["viewCount"]

    @pytest.mark.asyncio
    async def test_search_pagination(self, init_test_db, video_factory):
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
        )

        assert result.errors is None
        assert result.data["SearchVideos"]["pagination"]["currentPageNumber"] == 2
        assert result.data["SearchVideos"]["pagination"]["totalCount"] == 20
        assert result.data["SearchVideos"]["pagination"]["size"] == 15  # 搜索页默认每页15条


@pytest.mark.unit
class TestResolveGetTopTags:

    @pytest.mark.asyncio
    async def test_get_top_tags(self, init_test_db, sample_tags):
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
        )

        assert result.errors is None
        tags = result.data["getTopTags"]
        assert len(tags) > 0
        assert tags[0]["count"] >= tags[-1]["count"]

    @pytest.mark.asyncio
    async def test_top_tags_limit(self, init_test_db, tag_factory):
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
        )

        assert result.errors is None
        tags = result.data["getTopTags"]
        assert len(tags) <= 20  

    @pytest.mark.asyncio
    async def test_empty_tags(self, init_test_db):
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
        )

        assert result.errors is None
        assert result.data["getTopTags"] == []


@pytest.mark.unit
class TestResolveGetSuggestions:

    @pytest.mark.asyncio
    async def test_get_title_suggestions(self, init_test_db, sample_videos):
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
        )

        assert result.errors is None
        suggestions = result.data["getSuggestions"]
        assert isinstance(suggestions, list)
        if len(suggestions) > 0:
            assert isinstance(suggestions[0], str)
            assert "video" in suggestions[0].lower()

    @pytest.mark.asyncio
    async def test_get_author_suggestions(self, init_test_db, sample_videos):
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
        )

        assert result.errors is None
        suggestions = result.data["getSuggestions"]
        assert isinstance(suggestions, list)
        if len(suggestions) > 0:
            assert isinstance(suggestions[0], str)

    @pytest.mark.asyncio
    async def test_get_tag_suggestions(self, init_test_db, sample_tags):
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
        )

        assert result.errors is None
        suggestions = result.data["getSuggestions"]
        assert isinstance(suggestions, list)


@pytest.mark.unit
class TestResolveGetVideoById:

    @pytest.mark.asyncio
    async def test_get_existing_video(self, init_test_db, sample_videos):
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

        assert result.errors is not None
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_get_video_with_invalid_id(self, init_test_db):
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

        assert result.errors is not None
        assert len(result.errors) > 0


# @pytest.mark.unit
# class TestResolveBrowseDirectory:

#     @pytest.mark.asyncio
#     @pytest.mark.skip
#     async def test_browse_root_directory(self, init_test_db):
#         pass

#     @pytest.mark.asyncio
#     @pytest.mark.skip
#     async def test_browse_with_invalid_path(self, init_test_db):
#         pass
