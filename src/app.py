from fastapi import FastAPI, Request
import strawberry
from strawberry.fastapi import GraphQLRouter

from src.context import get_context, lifespan
from src.resolvers.video_stream_resolver import video_stream_resolver
from src.schema.mutation_schema import Mutation
from .schema.query_schema import Query
from fastapi.middleware.cors import CORSMiddleware

schema = strawberry.Schema(query=Query, mutation=Mutation)

def create_app():
    app = FastAPI(lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    graphql_app = GraphQLRouter(schema=schema, context_getter=get_context)
    app.include_router(graphql_app, prefix="/graphql")

    @app.get("/video/stream/{video_id}")
    async def stream_video(video_id: str, request: Request):
        """video stream endpoint"""
        return await video_stream_resolver(video_id, request)

    print("Application startup complete")

    return app