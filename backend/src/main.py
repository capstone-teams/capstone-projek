from fastapi import FastAPI

from src.middlewares.error_handlers import register_exception_handlers

app = FastAPI()

register_exception_handlers(app)

@app.get("/")
async def root():
    return {"message": "Moodle Agentic AI Backend"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}
