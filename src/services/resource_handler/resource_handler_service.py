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
    def _create_handler(
        category: str,
        pseudo_paths: dict[str, str],
        settings: Settings,
    ) -> BaseResourceHandler:
        handler_configs = settings.handler_config.get(category, {})

        if handler_configs:
            from src.services.resource_handler.s3.s3_handler import S3ResourceHandler
            return S3ResourceHandler(category, pseudo_paths, handler_configs)
        else:
            return LocalFSResourceHandler(category, pseudo_paths, settings.ROOT_PATH)

    def get_handler(self, category: str) -> BaseResourceHandler:
        handler = self._handlers.get(category)
        if handler is None:
            raise ValueError(f"No resource handler for category '{category}'")
        return handler

    def get_all_categories(self) -> list[str]:
        return list(self._handlers.keys())

    def get_pseudo_names(self, category: str) -> list[str]:
        settings = get_settings()
        if category not in settings.resource_paths:
            raise ValueError(f"Category '{category}' not found in config")
        return list(settings.resource_paths[category].keys())


@lru_cache
def get_resource_handler_service() -> ResourceHandlerService:
    return ResourceHandlerService()
