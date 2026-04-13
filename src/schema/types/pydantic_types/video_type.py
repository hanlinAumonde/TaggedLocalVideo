from typing import Optional
from pydantic import BaseModel, field_validator, model_validator

from src.config import get_settings


class SeriesFieldInputModel(BaseModel):
    name: Optional[str] = None
    order: Optional[int] = None
    clear: bool = False

    @field_validator("name", mode="after")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        settings = get_settings()
        max_length = settings.validation.series_name_max_length
        if len(v) > max_length:
            raise ValueError(f"Series name too long (max {max_length})")
        return v

    @model_validator(mode="after")
    def validate_combo(self) -> "SeriesFieldInputModel":
        if not self.clear and self.name is None:
            raise ValueError("SeriesFieldInput requires either clear=true or a non-empty name")
        return self


class UpdateVideoMetadataInputModel(BaseModel):
    videoId: str
    name: Optional[str] = None
    introduction: Optional[str] = None
    author: Optional[str] = None
    tags: list[str]
    loved: Optional[bool] = None
    series: Optional[SeriesFieldInputModel] = None

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