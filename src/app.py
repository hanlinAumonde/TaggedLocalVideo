from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import asynccontextmanager
from fastapi.responses import JSONResponse
from strawberry.fastapi import GraphQLRouter
from src.schema.strawberry_schema import schema
from src.db.setup_mongo import setup_mongo
from src.router import video_router
from fastapi.middleware.cors import CORSMiddleware
from src.config import get_settings
from src.logger import setup_logger, get_logger

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

async def global_exception_handler(request: Request, exc: HTTPException):
    logger.error(
        f"Unhandled exception: {exc.status_code} - {exc.detail}"
        f" on path: {request.url.path}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

def create_app():
    app = FastAPI(lifespan=lifespan)

    app.add_exception_handler(HTTPException, global_exception_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    graphql_app = GraphQLRouter(schema=schema)
    app.include_router(graphql_app, prefix="/graphql")
    app.include_router(video_router.router)


    logger.info("Application startup complete")

    return app
