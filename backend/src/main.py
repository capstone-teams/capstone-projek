from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Moodle Agentic AI Backend"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}
