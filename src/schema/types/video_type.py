from typing import Optional
import strawberry

from src.db.models.Video_model import VideoModel, VideoTagModel

@strawberry.type
class VideoTag:
    name: str
    count: int

@strawberry.type
class Video:
    id: strawberry.ID
    #path: str
    isDir: bool
    viewCount: int
    lastViewTime: float
    lastModifyTime: float
    name: str
    introduction: str
    author: str
    loved: bool
    size: int
    tags: list[VideoTag]

    # if None use default thumbnail in public/static/default_thumbnail.jpg
    # TODO: determine how to handle video thumbnails
    thumbnail: Optional[str] = None 

    @classmethod
    async def from_mongoDB(cls, videoModel: VideoModel) -> "Video":
        """
        Convert a VideoModel instance from MongoDB to a Video GraphQL type.
        """
        tag_names = videoModel.tags or []

        if tag_names:
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
            ]
        )
    
@strawberry.input
class UpdateVideoMetadataInput:
    videoId: strawberry.ID
    name: Optional[str] = None
    introduction: Optional[str] = None
    author: Optional[str] = None
    tags: list[str]
    loved: Optional[bool] = None