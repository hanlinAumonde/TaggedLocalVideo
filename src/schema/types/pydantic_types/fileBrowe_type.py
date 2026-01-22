from pydantic import BaseModel, ValidationInfo, field_validator


class RelativePathInputModel(BaseModel):
    refreshFlag: bool = False  # If True, bypass any caching
    
    relativePath: str | None = None  # If None, browse the root directory that contains all resources paths with their pesudo names

    parsedPath: tuple[str, str | None] | None = None  # (pesudo_root_dir_name, sub_path), not provided by user

    @field_validator("parsedPath", mode="after")
    @classmethod
    def parse_relative_path(cls, v: tuple[str, str | None] | None, info: ValidationInfo) -> tuple[str, str | None] | None:
        """
        validate and parse the relative path, set it to parsed_path
        valid format: 1. None (browse root)
                      2. <pseudo_root_dir_name>/<sub_path>
                      3. <pseudo_root_dir_name>
        """
        relativePath: str | None = info.data['relativePath']
        # validate the format
        if relativePath is None:
            return None
        # parse the relative path
        parts = relativePath.split("/", 1)
        result = (parts[0], "/"+parts[1] if len(parts) > 1 else None)
        return result
            