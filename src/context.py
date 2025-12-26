from fastapi import Depends
import yaml
from strawberry.fastapi import BaseContext

class AppContext(BaseContext):
    def __init__(self, resource_paths: list[dict], pagination_sizes: dict, suggestion_limits: dict):
        self.resource_paths = resource_paths
        self.pagination_sizes = pagination_sizes
        self.suggestion_limits = suggestion_limits

def custom_context_dependency() -> AppContext:
    with open("config.yaml", "r") as file:
        config = yaml.safe_load(file)
    return AppContext(
        resource_paths=config["resource_paths"],
        pagination_sizes=config["pagination_size"],
        suggestion_limits=config["suggestion_limit"]
    )

async def get_context(custom_context=Depends(custom_context_dependency)):
    return custom_context