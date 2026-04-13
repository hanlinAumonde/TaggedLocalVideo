from functools import lru_cache
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from envyaml import EnvYAML
from pydantic_settings import BaseSettings

class CacheConfig(BaseModel):
    max_size: int = 2048
    ttl: int = 3600  # in seconds
    cache_type: str = "cachetools"

class PageSize(BaseModel):
    homepage_videos: int = 10
    homepage_tags: int = 50
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
    series_name_max_length: int = 100


class LoggingConfig(BaseModel):
    log_dir: str = "logs"
    rotation: str = "10 MB"
    retention: str = "30 days"


class S3HandlerConfig(BaseModel):
    endpoint_url: str
    access_key: str
    secret_key: str
    bucket: str
    region: str = ""


class ThumbnailConfig(BaseModel):
    storage_category: str = ""
    storage_pseudo_name: str = ""


class Settings(BaseSettings):
    model_config = ConfigDict(extra="ignore")

    resource_paths: dict[str, dict[str, str]] = Field(default_factory=dict)
    handler_config: dict[str, dict[str, S3HandlerConfig]] = Field(default_factory=dict)
    thumbnail_config: ThumbnailConfig = ThumbnailConfig()
    ROOT_PATH: Optional[str] = None
    cache_config: CacheConfig = CacheConfig()
    ffmpeg_semaphore_limit: int = 4
    page_size_default: PageSize = PageSize()
    suggestion_limit: SuggestionLimit = SuggestionLimit()
    video_extensions: list[str] = Field(default_factory=lambda: [".mp4"])
    mongo: MongoConfig = MongoConfig()
    validation: ValidationConfig = ValidationConfig()
    logging: LoggingConfig = LoggingConfig()

    def get_valid_categories(self) -> list[str]:
        return list(self.resource_paths.keys())

    def get_all_host_paths(self) -> set[str]:
        """Flatten all host paths across all categories."""
        return {
            host_path
            for pseudo_paths in self.resource_paths.values()
            for host_path in pseudo_paths.values()
        }

    def get_host_path(self, category: str, pseudo_name: str) -> str:
        return self.resource_paths[category][pseudo_name]

    def find_category_by_host_path(self, host_path: str) -> str | None:
        """Reverse lookup: find category by matching host path prefix."""
        for category, pseudo_paths in self.resource_paths.items():
            for pseudo_name, configured_path in pseudo_paths.items():
                if host_path == configured_path or host_path.startswith(configured_path + "/"):
                    return category
        return None

    def get_all_logical_root_paths(self) -> set[str]:
        """Get all logical root paths in format '{category}/{pseudo_name}'."""
        return {
            f"{category}/{pseudo_name}"
            for category, pseudo_paths in self.resource_paths.items()
            for pseudo_name in pseudo_paths
        }


@lru_cache
def get_settings() -> Settings:
    config = dict(EnvYAML("config.yaml"))
    return Settings.model_validate(config)


