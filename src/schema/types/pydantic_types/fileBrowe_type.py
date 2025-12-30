from pydantic import BaseModel, ValidationInfo, field_validator


class RelativePathInputModel(BaseModel):
    # refreshFlag: bool = False  # If True, bypass any caching
    relativePath: str | None = None  # If None, browse the root directory that contains all resources paths with their pesudo names

    parsed_path: tuple[str, str | None] | None = None  # (pesudo_root_dir_name, sub_path), not provided by user

    @field_validator("relativePath", mode="after")
    @classmethod
    def parse_relative_path(cls, v: str | None, info: ValidationInfo) -> tuple[str, str | None] | None:
        """
        validate and parse the relative path, set it to parsed_path
        valid format: 1. None (browse root)
                      2. <pseudo_root_dir_name>/<sub_path>
                      3. <pseudo_root_dir_name>
        """
        # validate the format

        # parse the relative path
        parts = v.split("/", 1)
        return (parts[0], "/"+parts[1] if len(parts) > 1 else None)
        