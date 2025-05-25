from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from model import main

app = FastAPI()

# Настройка CORS (чтобы фронтенд мог обращаться к серверу)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Для разработки. В продакшене укажите конкретный домен фронтенда!
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/analyze")
async def analyze_text(video_id: str = Query(...)):
    try:
        print(video_id)
        return {"emotions": main(video_id, 100)}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ping")
async def ping():
    return {"status": "ok"}
