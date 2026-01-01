import pytest
from bson import ObjectId
from freezegun import freeze_time

from src.app import schema
from src.db.models.Video_model import VideoModel


@pytest.mark.unit
class TestResolveUpdateVideoMetadata:

    @pytest.mark.asyncio
    async def test_update_video_name(self, init_test_db, sample_videos):
        video = sample_videos[0]
        video_id = str(video.id)

        mutation = """
            mutation UpdateVideoName($input: UpdateVideoMetadataInput!) {
                updateVideoMetadata(input: $input) {
                    success
                    video {
                        id
                        name
                    }
                }
            }
        """

        result = await schema.execute(
            mutation,
            variable_values={
                "input": {
                    "videoId": video_id,
                    "name": "updated_name.mp4",
                    "tags": video.tags
                }
            }
        )

        assert result.errors is None
        assert result.data["updateVideoMetadata"]["success"] is True
        assert result.data["updateVideoMetadata"]["video"]["name"] == "updated_name.mp4"

        updated_video = await VideoModel.get(video.id)
        assert updated_video.name == "updated_name.mp4"

    @pytest.mark.asyncio
    async def test_update_video_author(self, init_test_db, sample_videos):
        video = sample_videos[0]
        video_id = str(video.id)

        mutation = """
            mutation UpdateVideoAuthor($input: UpdateVideoMetadataInput!) {
                updateVideoMetadata(input: $input) {
                    success
                    video {
                        id
                        author
                    }
                }
            }
        """

        result = await schema.execute(
            mutation,
            variable_values={
                "input": {
                    "videoId": video_id,
                    "author": "New Author",
                    "tags": video.tags
                }
            }
        )

        assert result.errors is None
        assert result.data["updateVideoMetadata"]["success"] is True
        assert result.data["updateVideoMetadata"]["video"]["author"] == "New Author"

        updated_video = await VideoModel.get(video.id)
        assert updated_video.author == "New Author"

    @pytest.mark.asyncio
    async def test_update_video_tags(self, init_test_db, sample_videos):
        video = sample_videos[0]
        video_id = str(video.id)
        new_tags = ["new_tag1", "new_tag2"]

        mutation = """
            mutation UpdateVideoTags($input: UpdateVideoMetadataInput!) {
                updateVideoMetadata(input: $input) {
                    success
                    video {
                        id
                        tags {
                            name
                        }
                    }
                }
            }
        """

        result = await schema.execute(
            mutation,
            variable_values={
                "input": {
                    "videoId": video_id,
                    "tags": new_tags
                }
            }
        )

        assert result.errors is None
        assert result.data["updateVideoMetadata"]["success"] is True
        returned_tags = [tag["name"] for tag in result.data["updateVideoMetadata"]["video"]["tags"]]
        assert set(returned_tags) == set(new_tags)

        updated_video = await VideoModel.get(video.id)
        assert set(updated_video.tags) == set(new_tags)
    
    @pytest.mark.asyncio
    async def test_update_loved_status(self, init_test_db, sample_videos):
        video = sample_videos[0]
        video_id = str(video.id)
        original_loved = video.loved

        mutation = """
            mutation UpdateLovedStatus($input: UpdateVideoMetadataInput!) {
                updateVideoMetadata(input: $input) {
                    success
                    video {
                        id
                        loved
                    }
                }
            }
        """

        result = await schema.execute(
            mutation,
            variable_values={
                "input": {
                    "videoId": video_id,
                    "loved": not original_loved,
                    "tags": video.tags
                }
            }
        )

        assert result.errors is None
        assert result.data["updateVideoMetadata"]["success"] is True
        assert result.data["updateVideoMetadata"]["video"]["loved"] is not original_loved

        updated_video = await VideoModel.get(video.id)
        assert updated_video.loved is not original_loved
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_video(self, init_test_db):
        fake_id = str(ObjectId())

        mutation = """
            mutation UpdateNonexistentVideo($input: UpdateVideoMetadataInput!) {
                updateVideoMetadata(input: $input) {
                    success
                    video {
                        id
                    }
                }
            }
        """

        result = await schema.execute(
            mutation,
            variable_values={
                "input": {
                    "videoId": fake_id,
                    "tags": []
                }
            }
        )

        # GraphQL 会捕获异常并返回在 errors 中
        assert result.errors is not None
        assert len(result.errors) > 0


@pytest.mark.unit
class TestResolveBatchUpdateVideoTags:

    @pytest.mark.asyncio
    async def test_batch_append_tags(self, init_test_db, sample_videos):
        video1_id = str(sample_videos[0].id)
        video2_id = str(sample_videos[1].id)

        mutation = """
            mutation BatchAppendTags($input: TagsOperationBatchInput!) {
                batchUpdateVideoTags(input: $input) {
                    success
                    successfulUpdatesMappings
                }
            }
        """

        result = await schema.execute(
            mutation,
            variable_values={
                "input": {
                    "append": True,
                    "mappings": [
                        { "videoId" :video1_id, "tags": ["new_tag1", "new_tag2"] },
                        { "videoId" :video2_id, "tags": ["new_tag3"] }
                    ]
                }
            }
        )

        assert result.errors is None
        assert result.data["batchUpdateVideoTags"]["success"] is True
        assert video1_id in result.data["batchUpdateVideoTags"]["successfulUpdatesMappings"]
        assert video2_id in result.data["batchUpdateVideoTags"]["successfulUpdatesMappings"]

        # 验证标签已添加
        video1 = await VideoModel.get(sample_videos[0].id)
        assert "new_tag1" in video1.tags
        assert "new_tag2" in video1.tags

    @pytest.mark.asyncio
    async def test_batch_remove_tags(self, init_test_db, sample_videos):
        """测试批量移除标签"""
        video = sample_videos[0]
        video_id = str(video.id)
        original_tags = video.tags.copy()

        # 假设 video 有标签 "action"
        if "action" not in original_tags:
            video.tags.append("action")
            await video.save()

        mutation = """
            mutation BatchRemoveTags($input: TagsOperationBatchInput!) {
                batchUpdateVideoTags(input: $input) {
                    success
                    successfulUpdatesMappings
                }
            }
        """

        result = await schema.execute(
            mutation,
            variable_values={
                "input": {
                    "append": False,
                    "mappings": [
                        {"videoId": video_id, "tags" : ["action"]}
                    ]
                }
            }
        )

        assert result.errors is None
        assert result.data["batchUpdateVideoTags"]["success"] is True

        # 验证标签已移除
        updated_video = await VideoModel.get(video.id)
        assert "action" not in updated_video.tags

    @pytest.mark.asyncio
    async def test_batch_update_with_invalid_video_id(self, init_test_db):
        """测试批量更新包含无效视频 ID"""
        fake_id = str(ObjectId())

        mutation = """
            mutation BatchUpdateInvalidId($input: TagsOperationBatchInput!) {
                batchUpdateVideoTags(input: $input) {
                    success
                    successfulUpdatesMappings
                }
            }
        """

        result = await schema.execute(
            mutation,
            variable_values={
                "input": {
                    "append": True,
                    "mappings": [
                        { "videoId":fake_id, "tags": ["tag1"] }
                    ]
                }
            }
        )

        # 应该不会抛出异常,但该视频 ID 不会在成功列表中
        # 具体行为取决于实现
        assert result.errors is None or result.data is not None
        if result.data:
            list_video_id = result.data["batchUpdateVideoTags"]["successfulUpdatesMappings"]
            assert fake_id not in list_video_id or len(list_video_id[fake_id]) == 0


@pytest.mark.unit
class TestResolveRecordVideoView:
    """测试 resolve_record_video_view 函数"""

    @pytest.mark.asyncio
    @freeze_time("2024-01-01 12:00:00")
    async def test_record_view_increments_count(self, init_test_db, sample_videos):
        """测试记录观看增加观看次数"""
        video = sample_videos[0]
        video_id = str(video.id)
        original_view_count = video.viewCount

        mutation = """
            mutation RecordVideoView($videoId: ID!) {
                recordVideoView(videoId: $videoId) {
                    success
                    video {
                        id
                        viewCount
                    }
                }
            }
        """

        result = await schema.execute(
            mutation,
            variable_values={"videoId": video_id}
        )

        assert result.errors is None
        assert result.data["recordVideoView"]["success"] is True
        assert result.data["recordVideoView"]["video"]["viewCount"] == original_view_count + 1

        # 验证数据库中的数据已更新
        updated_video = await VideoModel.get(video.id)
        assert updated_video.viewCount == original_view_count + 1

    @pytest.mark.asyncio
    @freeze_time("2024-01-01 12:00:00")
    async def test_record_view_updates_last_view_time(self, init_test_db, sample_videos):
        """测试记录观看更新最后观看时间"""
        video = sample_videos[0]
        video_id = str(video.id)

        mutation = """
            mutation RecordVideoView($videoId: ID!) {
                recordVideoView(videoId: $videoId) {
                    success
                    video {
                        id
                        lastViewTime
                    }
                }
            }
        """

        result = await schema.execute(
            mutation,
            variable_values={"videoId": video_id}
        )

        assert result.errors is None
        assert result.data["recordVideoView"]["success"] is True
        # 验证最后观看时间已更新(使用 freezegun 冻结时间)
        assert result.data["recordVideoView"]["video"]["lastViewTime"] > 0

    @pytest.mark.asyncio
    async def test_record_view_multiple_times(self, init_test_db, sample_videos):
        """测试多次记录观看"""
        video = sample_videos[0]
        video_id = str(video.id)
        original_view_count = video.viewCount

        mutation = """
            mutation RecordVideoView($videoId: ID!) {
                recordVideoView(videoId: $videoId) {
                    success
                    video {
                        viewCount
                    }
                }
            }
        """

        # 记录3次观看
        for _ in range(3):
            result = await schema.execute(
                mutation,
                variable_values={"videoId": video_id}
            )
            assert result.errors is None

        # 验证观看次数增加了3次
        updated_video = await VideoModel.get(video.id)
        assert updated_video.viewCount == original_view_count + 3

    @pytest.mark.asyncio
    async def test_record_view_nonexistent_video(self, init_test_db):
        """测试记录不存在的视频观看"""
        fake_id = str(ObjectId())

        mutation = """
            mutation RecordVideoView($videoId: ID!) {
                recordVideoView(videoId: $videoId) {
                    success
                }
            }
        """

        result = await schema.execute(
            mutation,
            variable_values={"videoId": fake_id}
        )

        # GraphQL 会捕获异常并返回在 errors 中
        assert result.errors is not None
        assert len(result.errors) > 0


@pytest.mark.unit
class TestResolveDeleteVideo:
    """测试 resolve_delete_video 函数"""

    @pytest.mark.asyncio
    async def test_delete_existing_video(self, init_test_db, sample_videos):
        """测试删除存在的视频"""
        video = sample_videos[0]
        video_id = str(video.id)

        mutation = """
            mutation DeleteVideo($videoId: ID!) {
                deleteVideo(videoId: $videoId) {
                    success
                }
            }
        """

        result = await schema.execute(
            mutation,
            variable_values={"videoId": video_id}
        )

        assert result.errors is None
        assert result.data["deleteVideo"]["success"] is True

        # 验证视频已从数据库中删除
        deleted_video = await VideoModel.get(video.id)
        assert deleted_video is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_video(self, init_test_db):
        """测试删除不存在的视频"""
        fake_id = str(ObjectId())

        mutation = """
            mutation DeleteVideo($videoId: ID!) {
                deleteVideo(videoId: $videoId) {
                    success
                }
            }
        """

        result = await schema.execute(
            mutation,
            variable_values={"videoId": fake_id}
        )

        # GraphQL 会捕获异常并返回在 errors 中
        assert result.errors is not None
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_delete_video_multiple_times(self, init_test_db, sample_videos):
        """测试多次删除同一视频"""
        video = sample_videos[0]
        video_id = str(video.id)

        mutation = """
            mutation DeleteVideo($videoId: ID!) {
                deleteVideo(videoId: $videoId) {
                    success
                }
            }
        """

        # 第一次删除应该成功
        result1 = await schema.execute(
            mutation,
            variable_values={"videoId": video_id}
        )
        assert result1.errors is None
        assert result1.data["deleteVideo"]["success"] is True

        # 第二次删除应该失败(视频已不存在)
        result2 = await schema.execute(
            mutation,
            variable_values={"videoId": video_id}
        )
        assert result2.errors is not None
        assert len(result2.errors) > 0
