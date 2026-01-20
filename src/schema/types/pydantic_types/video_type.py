from typing import Optional
from pydantic import BaseModel, field_validator

from src.config import get_settings


class UpdateVideoMetadataInputModel(BaseModel):
    videoId: str
    name: Optional[str] = None
    introduction: Optional[str] = None
    author: Optional[str] = None
    tags: list[str]
    loved: Optional[bool] = None

    @field_validator("name", mode="after")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        settings = get_settings()
        max_length = settings.validation.name_max_length
        if len(v) > max_length:
            raise ValueError(f"Name too long (max {max_length})")
        return v

    @field_validator("introduction", mode="after")
    @classmethod
    def validate_introduction(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        settings = get_settings()
        max_length = settings.validation.introduction_max_length
        if len(v) > max_length:
            raise ValueError(f"Introduction too long (max {max_length})")
        return v

    @field_validator("author", mode="after")
    @classmethod
    def validate_author(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        settings = get_settings()
        max_length = settings.validation.author_max_length
        if len(v) > max_length:
            raise ValueError(f"Author too long (max {max_length})")
        return v

    @field_validator("tags", mode="after")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        settings = get_settings()
        validation = settings.validation

        if len(v) > validation.max_tags_count:
            raise ValueError(f"Too many tags (max {validation.max_tags_count})")

        for tag in v:
            if len(tag) > validation.tag_max_length:
                raise ValueError(f"Tag '{tag}' too long (max {validation.tag_max_length})")

        return v