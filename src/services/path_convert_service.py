import os
from src.config import get_settings
from src.errors import FileBrowseError


class AbsolutePath:

    def __init__(self, abs_path: str | None, category: str | None = None):
        self.abs_path = abs_path
        self.category = category

    @classmethod
    def from_relative_path(cls, parsedPath: tuple[str, str | None, str | None] | None) -> 'AbsolutePath':
        """
        Create AbsolutePath from parsed relative path tuple.
        """
        if parsedPath is None:
            return cls(None, category=None)

        category, pseudo_name, sub_path = parsedPath
        abs_path = cls._resolve_path(category, pseudo_name, sub_path)
        return cls(abs_path, category=category)

    @classmethod
    def from_existing_path(cls, path: str, category: str) -> 'AbsolutePath':
        """Create AbsolutePath from an existing path (e.g. from DB or os.scandir) with known category."""
        return cls(path, category=category)

    @staticmethod
    def _resolve_path(category: str, pseudo_name: str | None, sub_path: str | None) -> str:
        settings = get_settings()

        if category not in settings.resource_paths:
            raise FileBrowseError(f"Category '{category}' not found in resource paths.")

        if pseudo_name is not None:
            if pseudo_name not in settings.resource_paths[category]:
                raise FileBrowseError(f"Pseudo name '{pseudo_name}' not found under category '{category}'.")

            if settings.ROOT_PATH:
                abs_resource_path = os.path.join(settings.ROOT_PATH, category, pseudo_name)
            else:
                abs_resource_path = settings.resource_paths[category][pseudo_name]
        else:
            abs_resource_path = category

        if sub_path is None:
            return abs_resource_path
        return abs_resource_path + sub_path

    def DB_format_path(self) -> str | None:
        if self.abs_path is None:
            return None
        handler = self._get_handler()
        return handler.convert_to_DB_format_path(self.abs_path)

    def FS_format_path(self) -> str | None:
        if self.abs_path is None:
            return None
        handler = self._get_handler()
        return handler.convert_to_FS_format_path(self.abs_path)

    def get_path(self) -> str | None:
        if self.abs_path is None:
            return None
        handler = self._get_handler()
        return handler.get_path_standard_format(self.abs_path)

    def update_path(self, new_abs_path: str) -> None:
        self.abs_path = new_abs_path

    def is_root_level(self) -> bool:
        return self.abs_path is None and self.category is None

    def is_category_level(self) -> bool:
        return self.abs_path is not None and self.category is not None and self.abs_path == self.category

    def _get_handler(self):
        from src.services.resource_handler.resource_handler_service import get_resource_handler_service
        if self.category is None:
            raise ValueError("Cannot convert path without a category")
        return get_resource_handler_service().get_handler(self.category)
