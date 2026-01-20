from typing import Optional
from pydantic import BaseModel, field_validator

from src.config import get_settings


class TagsOperationMappingInputModel(BaseModel):
    append: bool
    tags: list[str]

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


class VideosBatchOperationInputModel(BaseModel):
    videoIds: list[str]
    tagsOperation: Optional[TagsOperationMappingInputModel] = None
    author: Optional[str] = None

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