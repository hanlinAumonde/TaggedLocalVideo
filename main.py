from src.app import create_app

#application = create_app()

if __name__ == "__main__":
    print("Starting the application...")
    import uvicorn
    uvicorn.run("main:create_app", host="localhost", port=12000, log_level="info", factory=create_app)