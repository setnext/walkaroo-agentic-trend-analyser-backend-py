# ============================================================================
# FILE: app/models.py
# Pydantic models for request/response validation
# ============================================================================

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any

# Website configurations (import from scraper or define here)
WEBSITES = {
    'flipkart': {'base': 'https://www.flipkart.com/search?q=', 'domain': 'flipkart.com'},
    'reliancedigital': {'base': 'https://www.reliancedigital.in/search?q=', 'domain': 'reliancedigital.in'},
    'myntra': {'base': 'https://www.myntra.com/', 'domain': 'myntra.com'},
    'amazon': {'base': 'https://www.amazon.in/s?k=', 'domain': 'amazon.in'}
}


# ============================================================================
# REQUEST MODELS
# ============================================================================

class Filters(BaseModel):
    """Filter criteria for product search"""
    brand: List[str] = Field(..., min_items=1, description="List of brands (required)")
    size: Optional[List[str]] = Field(default=None, description="Shoe sizes")
    color: Optional[List[str]] = Field(default=None, description="Color preferences")
    gender: Optional[List[str]] = Field(default=None, description="Gender filter")
    category: Optional[str] = Field(default="", description="Product category")
    
    # Normalize inputs
    @validator('brand', 'size', 'color', 'gender', pre=True)
    def normalize_list_fields(cls, v):
        """Normalize list fields - trim whitespace and handle empty strings"""
        if v is None:
            return None
        if isinstance(v, list):
            return [str(item).strip() for item in v if item and str(item).strip()]
        return v
    
    @validator('category', pre=True)
    def normalize_category(cls, v):
        """Normalize category - trim whitespace"""
        if v is None:
            return ""
        return str(v).strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "brand": ["bata"],
                "size": ["9"],
                "color": ["Black"],
                "gender": ["womens"],
                "category": "slippers"
            }
        }


class ScrapeRequest(BaseModel):
    """Request model for scraping endpoint"""
    website: str = Field(default="flipkart", description="Website to scrape")
    filters: Filters
    
    @validator('website', pre=True)
    def validate_website(cls, v):
        """Validate and normalize website name"""
        if not v:
            return "flipkart"
        
        website_lower = v.lower().strip()
        
        if website_lower not in WEBSITES:
            raise ValueError(
                f"Website '{v}' is not supported. "
                f"Must be one of: {', '.join(WEBSITES.keys())}"
            )
        return website_lower
    
    class Config:
        json_schema_extra = {
            "example": {
                "website": "amazon",
                "filters": {
                    "brand": ["bata"],
                    "size": ["9"],
                    "color": ["Black"],
                    "gender": ["womens"],
                    "category": "slippers"
                }
            }
        }


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class Product(BaseModel):
    """Product model"""
    id: str
    name: str
    brand: str
    price: float
    original_price: float
    discount: int
    image_url: str
    product_url: str
    rating: float
    reviews: int
    gender: str
    size: str
    colour: str
    in_stock: bool
    is_trending: bool
    category: str
    savings: float
    scraped_at: str
    currency: str = "INR"
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "prod_0001",
                "name": "Bata Women's Black Slippers",
                "brand": "Bata",
                "price": 599.0,
                "original_price": 999.0,
                "discount": 40,
                "image_url": "https://example.com/image.jpg",
                "product_url": "https://amazon.in/product/123",
                "rating": 4.2,
                "reviews": 145,
                "gender": "Women",
                "size": "9",
                "colour": "Black",
                "in_stock": True,
                "is_trending": False,
                "category": "slippers",
                "savings": 400.0,
                "scraped_at": "2025-01-01 10:30:45",
                "currency": "INR"
            }
        }


class ScrapeResponse(BaseModel):
    """Response model for successful scraping"""
    success: bool = True
    website: str
    filters_applied: Dict[str, Any]
    total_products: int
    products: List[Product]
    timestamp: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "website": "amazon",
                "filters_applied": {
                    "brand": ["bata"],
                    "size": ["9"],
                    "color": ["Black"],
                    "gender": ["womens"],
                    "category": "slippers"
                },
                "total_products": 12,
                "products": [
                    {
                        "id": "prod_0001",
                        "name": "Bata Women's Black Slippers",
                        "brand": "Bata",
                        "price": 599.0,
                        "original_price": 999.0,
                        "discount": 40,
                        "rating": 4.2,
                        "reviews": 145,
                        "size": "9",
                        "colour": "Black",
                        "in_stock": True,
                        "category": "slippers"
                    }
                ],
                "timestamp": "2025-01-01 10:30:45"
            }
        }


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    openai_configured: bool
    google_configured: bool
    websites: List[str]
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "openai_configured": True,
                "google_configured": True,
                "websites": ["flipkart", "amazon", "myntra", "reliancedigital"]
            }
        }


class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = False
    error: str
    detail: Optional[str] = None
    timestamp: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "No products found matching the given filters",
                "detail": "Try adjusting your filter criteria",
                "timestamp": "2025-01-01 10:30:45"
            }
        }


class WebsitesResponse(BaseModel):
    """Response model for supported websites"""
    success: bool = True
    websites: List[str]
    total: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "websites": ["flipkart", "amazon", "myntra", "reliancedigital"],
                "total": 4
            }
        }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_supported_websites() -> List[str]:
    """Get list of supported websites"""
    return list(WEBSITES.keys())


def validate_filters(filters: Dict[str, Any]) -> bool:
    """Validate filter dictionary"""
    if not filters:
        return False
    
    # Brand is required
    if not filters.get('brand') or len(filters.get('brand', [])) == 0:
        return False
    
    return True