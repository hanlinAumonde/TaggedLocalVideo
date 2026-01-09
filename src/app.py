from fastapi import Depends, FastAPI
from fastapi.concurrency import asynccontextmanager
import strawberry
from strawberry.fastapi import GraphQLRouter

from src.db.setup_mongo import setup_mongo
from src.router import video_router
from src.schema.mutation_schema import Mutation
from .schema.query_schema import Query
from fastapi.middleware.cors import CORSMiddleware

schema = strawberry.Schema(query=Query, mutation=Mutation)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await setup_mongo()
    yield
    print("Application shutdown")

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


    print("Application startup complete")

    return app