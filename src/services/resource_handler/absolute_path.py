from src.config import get_settings
from src.errors import FileBrowseError
from src.services.resource_handler.base_resource_handler import BaseResourceHandler


class AbsolutePath:

    def __init__(self, abs_path: str | None, category: str | None = None):
        self.abs_path = abs_path
        self.category = category

    @classmethod
    def from_relative_path(cls, parsedPath: tuple[str, str | None, str | None] | None) -> 'AbsolutePath':
        """
        Create AbsolutePath from parsed relative path tuple.
        Delegates path resolution to the handler for the given category.

        :param parsedPath: A tuple of (category, pseudo_name, sub_path) or None for root level.
        :type parsedPath: tuple[str, str | None, str | None] | None
        :return: An AbsolutePath instance representing the resolved absolute path.
        :rtype: AbsolutePath
        """
        if parsedPath is None:
            return cls(None, category=None)

        category, pseudo_name, sub_path = parsedPath
        settings = get_settings()

        if category not in settings.resource_paths:
            raise FileBrowseError(f"Category '{category}' not found in resource paths.")

        if pseudo_name is not None and pseudo_name not in settings.resource_paths[category]:
            raise FileBrowseError(f"Pseudo name '{pseudo_name}' not found under category '{category}'.")

        handler = cls._get_handler(category)
        abs_path = handler.resolve_path(category, pseudo_name, sub_path)
        return cls(abs_path, category=category)

    @classmethod
    def from_existing_path(cls, path: str, category: str) -> 'AbsolutePath':
        """
        Create AbsolutePath from an existing path (e.g. from DB or os.scandir) with known category.

        :param path: The existing absolute path.
        :type path: str
        :param category: The category of the path.
        :type category: str
        :return: An AbsolutePath instance representing the existing path.
        :rtype: AbsolutePath
        """
        return cls(path, category=category)

    def DB_format_path(self) -> str | None:
        """Convert the absolute path to the DB storage format using the handler's conversion method."""
        if self.abs_path is None:
            return None
        handler = self._get_handler(self.category)
        return handler.convert_to_DB_format_path(self.abs_path)

    def FS_format_path(self) -> str | None:
        """Convert the absolute path to the file system format using the handler's conversion method."""
        if self.abs_path is None:
            return None
        handler = self._get_handler(self.category)
        return handler.convert_to_FS_format_path(self.abs_path)

    def get_path(self) -> str | None:
        """Get the absolute path in the standard format using the handler's method."""
        if self.abs_path is None:
            return None
        handler = self._get_handler(self.category)
        return handler.get_path_standard_format(self.abs_path)

    def update_path(self, new_abs_path: str) -> None:
        """Update the absolute path to a new value."""
        self.abs_path = new_abs_path

    def is_root_level(self) -> bool:
        """Check if this path represents the root level."""
        return self.abs_path is None and self.category is None

    def is_category_level(self) -> bool:
        """Check if this path represents a category level."""
        return self.abs_path is not None and self.category is not None and self.abs_path == self.category

    @staticmethod
    def _get_handler(category: str) -> BaseResourceHandler:
        """
        Get the resource handler for the given category.
        
        :param category: The category for which to get the handler.
        :type category: str
        :return: The resource handler for the given category.
        :rtype: BaseResourceHandler
        """
        from src.services.resource_handler.resource_handler_service import get_resource_handler_service
        if category is None:
            raise ValueError("Cannot convert path without a category")
        return get_resource_handler_service().get_handler(category)
