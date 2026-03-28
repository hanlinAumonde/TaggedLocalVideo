from pydantic import BaseModel, ValidationInfo, field_validator
from src.config import get_settings


class RelativePathInputModel(BaseModel):
    skipCache: bool = False  # If True, bypass any caching and get the latest info from disk

    recursiveCalculation: bool = True  # If True, calculate metadata for all subdirectories recursively; if False, only calculate for the specified directory without going into subdirectories

    relativePath: str | None = None  # If None, browse the root directory that contains all category names

    parsedPath: tuple[str, str | None, str | None]  | None = None  # not provided by user

    @field_validator("parsedPath", mode="after")
    @classmethod
    def parse_relative_path(cls, v: tuple | None, info: ValidationInfo) -> tuple[str, str | None, str | None] | None:
        """
        validate and parse the relative path, set it to parsed_path
        valid format: 1. None (browse root - show categories)
                      2. <category> (show pseudo names under category)
                      3. <category>/<pseudo_name> (browse pseudo root)
                      4. <category>/<pseudo_name>/<sub_path> (browse sub directory)
        """
        relativePath: str | None = info.data['relativePath']

        # validate the format
        if relativePath is None:
            return None
        if relativePath.startswith("/") or relativePath.endswith("/"):
            raise ValueError("relativePath should not start or end with '/'")
        if ".." in relativePath.split("/"):
            raise ValueError("relativePath should not contain '..'")

        settings = get_settings()
        parts = relativePath.split("/", 2)

        # validate category
        category = parts[0]
        if category not in settings.resource_paths:
            raise ValueError(f"Category '{category}' not found in configured resource paths")

        if len(parts) == 1:
            # category level only
            return (category, None, None)

        # validate pseudo name
        pseudo_name = parts[1]
        if pseudo_name not in settings.resource_paths[category]:
            raise ValueError(f"Pseudo name '{pseudo_name}' not found under category '{category}'")

        if len(parts) == 2:
            return (category, pseudo_name, None)

        return (category, pseudo_name, "/" + parts[2])
