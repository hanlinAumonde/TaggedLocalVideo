from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
import strawberry
from strawberry.fastapi import GraphQLRouter

from src.db.setup_mongo import setup_mongo
from src.router import video_router
from src.schema.mutation_schema import Mutation
from .schema.query_schema import Query
from fastapi.middleware.cors import CORSMiddleware
from src.config import get_settings
from src.logger import setup_logger, get_logger

schema = strawberry.Schema(query=Query, mutation=Mutation)

# Initialize logger
settings = get_settings()

logger = get_logger("app")

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logger(
        log_dir=settings.logging.log_dir,
        rotation=settings.logging.rotation,
        retention=settings.logging.retention,
    )
    await setup_mongo()
    yield
    logger.info("Application shutdown")

def create_app():
    app = FastAPI(lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    graphql_app = GraphQLRouter(schema=schema)
    app.include_router(graphql_app, prefix="/graphql")
    app.include_router(video_router.router)


    logger.info("Application startup complete")

    return app
