from pydantic import BaseModel, Field, HttpUrl, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

class WebsiteEnum(str, Enum):
    """Supported e-commerce websites"""
    flipkart = "flipkart"
    amazon = "amazon"
    myntra = "myntra"
    reliancedigital = "reliancedigital"
    
class PriceRange(BaseModel):
    """Price range filter"""
    min: Optional[float] = Field(default=0, ge=0, description="Minimum price")
    max: Optional[float] = Field(default=None, ge=0, description="Maximum price")
    
    class Config:
        schema_extra = {
            "example": {
                "min": 500,
                "max": 2000
            }
        }


class ProductFilters(BaseModel):
    """Filter criteria for product search"""
    brand: List[str] = Field(..., min_items=1, description="At least one brand required")
    size: Optional[List[str]] = Field(default=None, description="Shoe sizes (e.g., ['8', '9', '10'])")
    color: Optional[List[str]] = Field(default=None, description="Colors (e.g., ['Black', 'White'])")
    gender: Optional[List[str]] = Field(default=None, description="Gender (e.g., ['Men', 'Women'])")
    category: Optional[str] = Field(default="", description="Product category (e.g., 'sports shoes')")
    price_range: Optional[PriceRange] = Field(default=None, description="Price range filter")
    
    class Config:
        schema_extra = {
            "example": {
                "brand": ["Nike", "Adidas"],
                "size": ["8", "9", "10"],
                "color": ["Black", "White"],
                "gender": ["Men"],
                "category": "sports shoes",
                "price_range": {
                    "min_price": 200,
                    "max_price": 5000
                }
            }
        }


class ScrapeRequest(BaseModel):
    """API request model for scraping"""
    website: WebsiteEnum = Field(default=WebsiteEnum.flipkart, description="E-commerce website to scrape")
    filters: ProductFilters = Field(..., description="Product filters")
    max_results: Optional[int] = Field(default=30, ge=1, le=100, description="Maximum products to fetch")
    
    class Config:
        schema_extra = {
            "example": {
                "website": "flipkart",
                "filters": {
                    "brand": ["Nike"],
                    "size": ["9"],
                    "color": ["Black"],
                    "gender": ["Men"],
                    "category": "slippers"
                },
                "max_results": 50
            }
        }


class ProductCategory(str, Enum):
    """Product categorization for trending/top-selling"""
    TRENDING = "trending"
    TOP_SELLING = "top_selling"
    NORMAL = "normal"


class Product(BaseModel):
    """Product data model - all fields optional except core ones to prevent dropping products"""
    id: Optional[str] = Field(default=None)
    name: Optional[str] = Field(default="Unknown Product")
    brand: Optional[str] = Field(default="Unknown")
    price: Optional[float] = Field(default=0.0, ge=0)
    original_price: Optional[float] = Field(default=0.0, ge=0)
    discount: Optional[int] = Field(default=0, ge=0, le=100)
    savings: Optional[float] = Field(default=0.0, ge=0)
    image_url: Optional[str] = Field(default=None)
    product_url: Optional[str] = Field(default=None)
    rating: Optional[float] = Field(default=0.0, ge=0, le=5)
    reviews: Optional[int] = Field(default=0, ge=0)
    gender: Optional[str] = Field(default="Unknown")
    size: Optional[str] = Field(default="Unknown")
    colour: Optional[str] = Field(default="Unknown")
    category: Optional[str] = Field(default="footwear")
    in_stock: Optional[bool] = Field(default=True)
    availability_status: Optional[str] = Field(default="in_stock")  # in_stock, out_of_stock, limited_stock
    is_trending: Optional[bool] = Field(default=False)
    product_classification: Optional[ProductCategory] = Field(default=ProductCategory.NORMAL)
    scraped_at: Optional[str] = Field(default=None)
    currency: Optional[str] = Field(default="INR")
    source_website: Optional[str] = Field(default=None)
    
    @validator('image_url', pre=True, always=True)
    def validate_image_url(cls, v):
        """Ensure image URL is valid or use placeholder"""
        if not v or not isinstance(v, str) or not v.startswith('http'):
            return 'https://via.placeholder.com/600x600?text=No+Image'
        return v
    
    @validator('product_url', pre=True, always=True)
    def validate_product_url(cls, v):
        """Ensure product URL is valid"""
        if not v or not isinstance(v, str) or not v.startswith('http'):
            return '#'
        return v
    
    @validator('original_price', pre=True, always=True)
    def validate_original_price(cls, v, values):
        """Set original_price to price if not provided"""
        if not v or v == 0:
            return values.get('price', 0)
        return v
    
    @validator('availability_status', pre=True, always=True)
    def set_availability_status(cls, v, values):
        """Set availability status based on in_stock"""
        in_stock = values.get('in_stock', True)
        if v:
            return v
        return "in_stock" if in_stock else "out_of_stock"
    
    class Config:
        use_enum_values = True


class ScrapeResponse(BaseModel):
    """API response model"""
    success: bool = Field(..., description="Whether the scraping was successful")
    website: str = Field(..., description="Website that was scraped")
    filters_applied: ProductFilters = Field(..., description="Filters that were applied")
    total_products: int = Field(..., description="Total number of products found")
    products: List[Product] = Field(default=[], description="List of products")
    timestamp: str = Field(..., description="Timestamp of the response")
    error: Optional[str] = Field(default=None, description="Error message if any")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    openai_configured: bool
    google_configured: bool
    websites: List[str]
    timestamp: str


class SearchResult(BaseModel):
    """Internal model for search results"""
    url: str
    title: str


class ScrapedPage(BaseModel):
    """Internal model for scraped pages"""
    url: str
    title: str
    html: str

