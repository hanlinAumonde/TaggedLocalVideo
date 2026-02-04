from typing import Optional
import strawberry

from src.db.models.Video_model import VideoModel, VideoTagModel
from src.schema.types.pydantic_types.video_type import UpdateVideoMetadataInputModel

@strawberry.type
class VideoTag:
    name: str
    count: int

@strawberry.type
class Video:
    id: strawberry.ID
    isDir: bool
    viewCount: int
    lastViewTime: float
    lastModifyTime: float
    name: str
    introduction: str
    author: str
    loved: bool
    size: float
    tags: list[VideoTag]
    duration: float

    # if None use default thumbnail in public/static/default_thumbnail.jpg
    # TODO: determine how to handle video thumbnails
    thumbnail: Optional[str] = None 

    @classmethod
    async def from_mongoDB(cls, videoModel: VideoModel, getTagsCount: bool = False) -> "Video":
        """
        Convert a VideoModel instance from MongoDB to a Video GraphQL type.
        """
        tag_names = videoModel.tags or []

        if tag_names and getTagsCount:
            tag_models = await VideoTagModel.find({"name": {"$in": tag_names}}).to_list()
            tag_dict = {tag.name: tag.tag_count for tag in tag_models}
        else:
            tag_dict = {}

        return cls(
            id=str(videoModel.id),
            isDir=videoModel.isDir,
            viewCount=videoModel.viewCount or 0,
            lastViewTime=videoModel.lastViewTime or 0.0,
            lastModifyTime=videoModel.lastModifyTime,
            name=videoModel.name,
            introduction=videoModel.introduction or "",
            author=videoModel.author or "Unknown",
            loved=videoModel.loved or False,
            size=int(videoModel.size),
            tags=[
                VideoTag(name=tag_name, count=tag_dict.get(tag_name, 0))
                for tag_name in tag_names
            ],
            thumbnail=videoModel.thumbnail,
            duration=videoModel.duration or 0.0
        )
    
    @classmethod
    def create_new(cls, id: strawberry.ID, name: str, isDir: bool, lastModifyTime: float, size: float, duration: float = 0.0) -> "Video":
        """
        Create a new Video instance with default values.
        """
        return cls(
            id=id,
            isDir=isDir,
            viewCount=0,
            lastViewTime=0.0,
            lastModifyTime=lastModifyTime,
            name=name,
            introduction="",
            author="Unknown",
            loved=False,
            size=size,
            tags=[],
            thumbnail=None,
            duration=duration
        )
    
@strawberry.experimental.pydantic.input(model=UpdateVideoMetadataInputModel)
class UpdateVideoMetadataInput:
    videoId: strawberry.auto
    name: strawberry.auto
    introduction: strawberry.auto
    author: strawberry.auto
    tags: strawberry.auto
    loved: strawberry.auto