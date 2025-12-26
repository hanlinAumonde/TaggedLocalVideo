from fastapi import FastAPI
import strawberry
from strawberry.fastapi import GraphQLRouter
from contextlib import asynccontextmanager

from src.context import get_context
from src.schema.mutation_schema import Mutation
from .db.setup_mongo import setup_mongo
from .schema.query_schema import Query
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    await setup_mongo()
    yield
    print("Application shutdown")

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

    print("Application startup complete")

    return app