from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.similar_products import ImageSearchService
from app.image_engineering import router as image_router
from fastapi.responses import JSONResponse
from fastapi import status
from app.scraper import scrape_products
from app.models.models import ScrapeRequest, ScrapeResponse
from fastapi.staticfiles import StaticFiles  # ⭐ ADD THIS
from app.similar_products import ImageSearchService
from app.image_engineering import router as image_router, STATIC_FILES_PATH  # ⭐ IMPORT STATIC_FILES_PATH
from fastapi.responses import JSONResponse
import time
import os
import logging
import requests
from starlette.responses import StreamingResponse, Response
from urllib.parse import unquote



logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
app.mount("/image/static", StaticFiles(directory=STATIC_FILES_PATH), name="static")


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

@app.post("/api/scrape", response_model=ScrapeResponse, tags=["Scraping"])
async def scrape_products_endpoint(request: ScrapeRequest):
    """
    Main product scraping endpoint
    
    **Request Body:**
    ```json
    {
        "website": "flipkart",
        "filters": {
            "brand": ["Nike", "Adidas"],
            "size": ["8", "9", "10"],
            "color": ["Black", "White"],
            "gender": ["Men"],
            "category": "sports shoes"
        },
        "max_results": 50
    }
    ```
    
    **Features:**
    - Searches Google for product URLs
    - Scrapes product pages in parallel
    - Extracts data using AI
    - Filters and validates products
    - Classifies products (trending/top-selling/normal)
    - Returns products with availability status
    - Handles out-of-stock products correctly
    - Deduplicates results
    
    **Returns:**
    - List of products matching the filters
    - Includes in-stock and out-of-stock products
    - Images can be loaded via `/api/image-proxy` endpoint
    """
    try:
        logger.info(f"Scrape request: {request.website}, filters: {request.filters.dict()}")
        
        # Validate
        if not request.filters.brand:
            raise HTTPException(
                status_code=400,
                detail="At least one brand is required in filters"
            )
        
        # Scrape products
        start_time = time.time()
        products = scrape_products(
            website=request.website.value,
            filters=request.filters,
            max_results=request.max_results
        )
        
        elapsed_time = time.time() - start_time
        logger.info(f"Scraping completed in {elapsed_time:.2f}s, found {len(products)} products")
        
        # Build response
        response = ScrapeResponse(
            success=True,
            website=request.website.value,
            filters_applied=request.filters,
            total_products=len(products),
            products=products,
            timestamp=time.strftime('%Y-%m-%d %H:%M:%S'),
            error=None
        )
        
        return response
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Scraping error: {str(e)}", exc_info=True)
        
        return ScrapeResponse(
            success=False,
            website=request.website.value if request.website else "unknown",
            filters_applied=request.filters,
            total_products=0,
            products=[],
            timestamp=time.strftime('%Y-%m-%d %H:%M:%S'),
            error=str(e)
        )


# ============================================================================
# IMAGE PROXY ENDPOINT
# ============================================================================

@app.get("/api/image-proxy", tags=["Utilities"])
async def image_proxy(url: str):
    """
    Image proxy endpoint to serve product images through backend
    
    **Purpose:**
    - Fixes Amazon/Flipkart image loading issues
    - Handles URL encoding problems
    - Prevents CORS errors
    - Caches images on backend
    
    **Usage:**
    ```
    GET /api/image-proxy?url=https://m.media-amazon.com/images/I/51abc+xyz.jpg
    ```
    
    **Frontend Usage:**
    ```javascript
    const proxyUrl = `/api/image-proxy?url=${encodeURIComponent(product.image_url)}`;
    <img src={proxyUrl} alt="Product" />
    ```
    """
    try:
        if not url or not url.startswith('http'):
            raise HTTPException(status_code=400, detail="Invalid image URL")
        
        # Decode URL if needed
        decoded_url = unquote(url)
        
        logger.info(f"Proxying image: {decoded_url[:100]}")
        
        # Fetch image with proper headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.amazon.in/' if 'amazon' in url else 'https://www.flipkart.com/'
        }
        
        response = requests.get(decoded_url, headers=headers, timeout=10, stream=True)
        response.raise_for_status()
        
        # Get content type
        content_type = response.headers.get('Content-Type', 'image/jpeg')
        
        # Stream response
        return StreamingResponse(
            response.iter_content(chunk_size=8192),
            media_type=content_type,
            headers={
                'Cache-Control': 'public, max-age=86400',  # Cache for 24 hours
                'Access-Control-Allow-Origin': '*'
            }
        )
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Image proxy error: {str(e)}")
        # Return placeholder image on error
        placeholder_url = "https://via.placeholder.com/600x600?text=Image+Not+Available"
        placeholder_response = requests.get(placeholder_url)
        return Response(
            content=placeholder_response.content,
            media_type="image/png"
        )
    except Exception as e:
        logger.error(f"Unexpected error in image proxy: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Image proxy error: {str(e)}")