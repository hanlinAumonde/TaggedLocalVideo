from src.app import create_app
from src.logger import get_logger

if __name__ == "__main__":
    import uvicorn

    logger = get_logger("main")
    logger.info("Starting application using Uvicorn")
    uvicorn.run("main:create_app", host="localhost", port=12000, log_level="info", factory=create_app)