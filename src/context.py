from fastapi import Depends, FastAPI
from fastapi.concurrency import asynccontextmanager
import yaml
from strawberry.fastapi import BaseContext

from src.db import setup_mongo

@asynccontextmanager
async def lifespan(app: FastAPI):
    await setup_mongo()
    yield
    print("Application shutdown")

class AppContext(BaseContext):
    def __init__(
            self, resource_paths: dict, 
            pagination_sizes: dict, 
            suggestion_limits: dict,
            video_extensions: list[str]
            ):
        self.resource_paths = resource_paths
        self.pagination_sizes = pagination_sizes
        self.suggestion_limits = suggestion_limits
        self.video_extensions = video_extensions

def custom_context_dependency() -> AppContext:
    with open("config.yaml", "r") as file:
        config = yaml.safe_load(file)
    return AppContext(
        resource_paths=config["resource_paths"],
        pagination_sizes=config["page_size_default"],
        suggestion_limits=config["suggestion_limit"],
        video_extensions=config["video_extensions"]
    )

def get_context(custom_context=Depends(custom_context_dependency)) -> AppContext:
    return custom_context