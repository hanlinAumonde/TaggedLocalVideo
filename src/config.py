from functools import lru_cache
from pydantic import BaseModel, Field
import yaml
from pydantic_settings import BaseSettings


class PageSize(BaseModel):
    homepage_videos: int = 5
    homepage_tags: int = 20
    searchpage: int = 15


class SuggestionLimit(BaseModel):
    name: int = 10
    author: int = 10
    tag: int = 20


class MongoConfig(BaseModel):
    host: str = "localhost"
    port: int = 27017
    username: str = ""
    password: str = ""
    database: str = "video_tag_db"


class ValidationConfig(BaseModel):
    name_max_length: int = 200
    author_max_length: int = 50
    introduction_max_length: int = 2000
    tag_max_length: int = 30
    max_tags_count: int = 50
    page_number_min: int = 1
    page_number_max: int = 10000


class Settings(BaseSettings):
    resource_paths: dict[str, str] = Field(default_factory=dict)
    page_size_default: PageSize = PageSize()
    suggestion_limit: SuggestionLimit = SuggestionLimit()
    video_extensions: list[str] = Field(default_factory=lambda: [".mp4"])
    mongo: MongoConfig = MongoConfig()
    validation: ValidationConfig = ValidationConfig()


@lru_cache
def get_settings() -> Settings:
    with open("config.yaml", "r", encoding="utf-8") as file:
        config: dict = yaml.safe_load(file) or {}
    return Settings.model_validate(config)


