from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import uvicorn
from app.similar_products import ImageSearchService

# -------------------------------------------------
# App setup
# -------------------------------------------------
app = FastAPI(title="Image Similarity API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/")
def health_check():
    return {"status": "API is running"}


@app.post("/similar-products")
async def get_similar_products(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    image_bytes = await file.read()

    if len(image_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image size must be under 5MB")

    try:
        searcher = ImageSearchService()
        results = searcher.search_similar_images(image_bytes, filename=file.filename)
        return {"results": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
