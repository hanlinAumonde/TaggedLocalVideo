from functools import lru_cache

from src.config import Settings, get_settings
from src.services.resource_handler.base_resource_handler import BaseResourceHandler
from src.services.resource_handler.local_fs.local_fs_handler import LocalFSResourceHandler


class ResourceHandlerService:
    """Dispatcher that selects the correct resource handler based on category."""

    def __init__(self):
        settings = get_settings()
        self._handlers: dict[str, BaseResourceHandler] = {}

        for category, pseudo_paths in settings.resource_paths.items():
            self._handlers[category] = self._create_handler(
                category, pseudo_paths, settings
            )

    @staticmethod
    def _create_handler(category: str,
                        pseudo_paths: dict[str, str],
                        settings: Settings) -> BaseResourceHandler:
        """
        Factory method to create a resource handler instance based on category and config.

        :param category: The category of the resource handler to create.
        :type category: str
        :param pseudo_paths: The mapping of pseudo paths for the category.
        :type pseudo_paths: dict[str, str]
        :param settings: The application settings containing handler configurations.
        :type settings: Settings
        :return: An instance of a resource handler for the specified category.
        :rtype: BaseResourceHandler
        """
        handler_configs = settings.handler_config.get(category, {})

        if handler_configs:
            from src.services.resource_handler.s3.s3_handler import S3ResourceHandler
            return S3ResourceHandler(category, pseudo_paths, handler_configs)
        else:
            return LocalFSResourceHandler(category, pseudo_paths, settings.ROOT_PATH)

    def get_handler(self, category: str) -> BaseResourceHandler:
        """
        Get the resource handler for the specified category.

        :param category: The category for which to retrieve the resource handler.
        :type category: str
        :return: The resource handler instance for the specified category.
        :rtype: BaseResourceHandler
        :raises ValueError: If no resource handler is found for the specified category.
        """
        handler = self._handlers.get(category)
        if handler is None:
            raise ValueError(f"No resource handler for category '{category}'")
        return handler

    def get_all_categories(self) -> list[str]:
        """Get a list of all categories that have resource handlers."""
        return list(self._handlers.keys())

    def get_pseudo_names(self, category: str) -> list[str]:
        """
        Get a list of all pseudo names for the specified category.

        :param category: The category for which to retrieve pseudo names.
        :type category: str
        :return: A list of pseudo names for the specified category.
        :rtype: list[str]
        :raises ValueError: If the category is not found in the configuration.
        """
        settings = get_settings()
        if category not in settings.resource_paths:
            raise ValueError(f"Category '{category}' not found in config")
        return list(settings.resource_paths[category].keys())


@lru_cache
def get_resource_handler_service() -> ResourceHandlerService:
    return ResourceHandlerService()
