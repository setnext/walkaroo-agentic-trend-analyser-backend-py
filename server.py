from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.similar_products import ImageSearchService
from app.image_engineering import router as image_router
from fastapi.responses import JSONResponse
from fastapi import status
# from app.scraper import scrape_products_pipeline
# from app.models.models import ScrapeRequest, ScrapeResponse
from fastapi.staticfiles import StaticFiles  # ⭐ ADD THIS
from app.similar_products import ImageSearchService
from app.image_engineering import router as image_router, STATIC_FILES_PATH  # ⭐ IMPORT STATIC_FILES_PATH
from fastapi.responses import JSONResponse
import os
import base64
from app.bom_orthographic_view import BomViewSearchService


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

# Include image engineering routes
app.include_router(image_router)


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
        results = searcher.search_similar_images(
            image_bytes,
            filename=file.filename
        )
        return {"results": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# @app.post("/api/scrape", response_model=ScrapeResponse, tags=["Scraping"])
# async def scrape_products(request: ScrapeRequest):
#     """
#     Main scraping endpoint with filter support
    
#     **Request Body:**
#     - `website`: Website to scrape (flipkart, amazon, myntra, reliancedigital)
#     - `filters`: Filter criteria
#         - `brand`: List of brands (REQUIRED)
#         - `size`: List of sizes (optional)
#         - `color`: List of colors (optional)
#         - `gender`: List of genders (optional)
#         - `category`: Product category (optional)
    
#     **Returns:**
#     - List of matching products with full details
    
#     **Example:**
#     ```json
#     {
#         "website": "flipkart",
#         "filters": {
#             "brand": ["Nike", "Adidas"],
#             "size": ["8", "9", "10"],
#             "color": ["Black", "White"],
#             "gender": ["Men"],
#             "category": "sports shoes"
#         }
#     }
#     ```
#     """
#     try:
#         # Convert Pydantic model to dict
#         filters_dict = request.filters.dict(exclude_none=True)
        
#         # Run scraping pipeline
#         result = await scrape_products_pipeline(
#             filters=filters_dict,
#             website=request.website
#         )
        
#         # Check if scraping was successful
#         if not result.get('success', False):
#             error_msg = result.get('error', 'Unknown error occurred')
#             raise HTTPException(
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 detail=error_msg
#             )
        
#         # Check if no products found
#         if result.get('total_products', 0) == 0:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="No products found matching the given filters"
#             )
        
#         return JSONResponse(content=result, status_code=status.HTTP_200_OK)
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         import traceback
#         error_detail = traceback.format_exc()
#         print(f"\n❌ ERROR: {e}")
#         print(error_detail)
        
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Internal server error: {str(e)}"
#         )


@app.post("/bom-orthographic-view")
async def bom_orthographic_view(file: UploadFile = File(...)):
    print("Received request for /bom-orthographic-view", file.filename)
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    image_bytes = await file.read()

    if len(image_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image size must be under 5MB")

    try:
        searcher = BomViewSearchService()
        top_view = searcher.orthographic_image_generation(
            image_bytes,
            filename=file.filename
        )
        side_view = searcher.orthographic_side_image_generation(
            image_bytes,
            filename=file.filename
        )
        bom_details = searcher.generate_bom_from_image(
            image_bytes,
            filename=file.filename
        )
        return {
            "top_view": base64.b64encode(top_view).decode("utf-8"),
            "side_view": base64.b64encode(side_view).decode("utf-8"),
            "bom_details":bom_details
            
        }    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
