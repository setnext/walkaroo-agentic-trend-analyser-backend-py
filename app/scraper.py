# import asyncio
# import json
# import os
# import re
# import time
# from typing import List, Dict, Optional
# from concurrent.futures import ThreadPoolExecutor, as_completed
# from urllib.parse import quote, unquote

# import requests
# from bs4 import BeautifulSoup
# from playwright.sync_api import sync_playwright
# import openai
# from dotenv import load_dotenv

# from app.models.models import ProductFilters, Product, ProductCategory,PriceRange

# # Load environment variables
# load_dotenv()
# openai.api_key = os.getenv('OPENAI_API_KEY')
# GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
# GOOGLE_CX = os.getenv('GOOGLE_CX')

# # Website configurations
# WEBSITES = {
#     'flipkart': {'base': 'https://www.flipkart.com/search?q=', 'domain': 'flipkart.com'},
#     'reliancedigital': {'base': 'https://www.reliancedigital.in/search?q=', 'domain': 'reliancedigital.in'},
#     'myntra': {'base': 'https://www.myntra.com/', 'domain': 'myntra.com'},
#     'amazon': {'base': 'https://www.amazon.in/s?k=', 'domain': 'amazon.in'}
# }


# # # ============================================================================
# # # STEP 1: BUILD SEARCH QUERY & FIND PRODUCT URLS
# # # ============================================================================

# def build_search_query(filters: ProductFilters) -> str:
#     """Build optimized search query from filters"""
#     parts = []
    
#     # Brand (required)
#     if filters.brand:
#         parts.extend(filters.brand)
    
#     # Category
#     if filters.category:
#         parts.append(filters.category)
    
#     # Gender
#     if filters.gender:
#         parts.extend([g.lower() for g in filters.gender])
    
#     # Color (optional - makes query specific)
#     if filters.color and len(filters.color) <= 3:
#         parts.extend([c.lower() for c in filters.color])
    
# #     query = ' '.join(parts)
# #     print(f"🔍 Search Query: {query}")
# #     return query


# # def is_product_page(url: str, domain: str) -> bool:
# #     """Check if URL is an actual product page"""
# #     url_lower = url.lower()
    
#     # Skip these patterns
#     skip_patterns = [
#         '/search?', '/s?k=', '/brand/', '/pr?sid=', '/collection/',
#         '/shop/', '/store/', '/help/', '/about', '/contact'
#     ]
    
# #     if any(p in url_lower for p in skip_patterns):
# #         return False
    
#     # Accept product page patterns
#     if 'flipkart.com' in domain:
#         return '/p/' in url_lower or '/itm/' in url_lower
#     elif 'amazon.in' in domain:
#         return '/dp/' in url_lower or '/gp/product/' in url_lower
#     elif 'myntra.com' in domain:
#         return re.search(r'/\d+/buy', url_lower) is not None
    
#     # If URL is long and doesn't match skip patterns, assume it's a product
#     return len(url) > 50


# def search_product_urls(query: str, website: str, max_results: int = 100) -> List[Dict[str, str]]:
#     """Search Google for PRODUCT pages only (skip category pages)"""
#     if not GOOGLE_API_KEY or not GOOGLE_CX:
#         print("❌ Google API not configured!")
#         return []
    
# #     print(f"\n🔍 Searching Google: '{query}' on {website}")
    
# #     website_config = WEBSITES.get(website.lower(), WEBSITES['flipkart'])
# #     site_domain = website_config['domain']
    
#     all_urls = []
#     num_requests = min((max_results + 9) // 10, 10)
    
# #     for start_index in range(1, num_requests * 10 + 1, 10):
# #         try:
# #             params = {
# #                 'key': GOOGLE_API_KEY,
# #                 'cx': GOOGLE_CX,
# #                 'q': f'{query} site:{site_domain}',
# #                 'start': start_index,
# #                 'num': 10,
# #                 'gl': 'in',
# #                 'hl': 'en'
# #             }
            
#     response = requests.get(
#                 'https://www.googleapis.com/customsearch/v1',
#                 params=params,
#                 timeout=10
#             )
            
#             if response.status_code != 200:
#                 print(f"   ⚠️ Status {response.status_code}, stopping pagination")
#                 break
            
#             data = response.json()
#             if 'items' not in data:
#                 print(f"   ℹ️ No more results at index {start_index}")
#                 break
            
# #             for item in data['items']:
# #                 url = item.get('link', '')
# #                 title = item.get('title', '')
                
#                 # ONLY accept actual product pages
#                 if is_product_page(url, site_domain):
#                     all_urls.append({'url': url, 'title': title})
            
#             print(f"   Found: {len(data['items'])} URLs (Products: {len(all_urls)})")
#             time.sleep(0.5)  # Rate limiting
            
# #         except Exception as e:
# #             print(f"❌ Search Error: {e}")
# #             break
    
# #     print(f"✅ Total Product URLs: {len(all_urls)}")
# #     return all_urls


# # ============================================================================
# # STEP 2: SCRAPE PRODUCT PAGES
# # ============================================================================

# def scrape_product_page(url: str, timeout: int = 20) -> Optional[str]:
#     """Scrape individual product page for full details"""
#     try:
#         with sync_playwright() as p:
#             browser = p.chromium.launch(headless=True)
#             context = browser.new_context(
#                 viewport={'width': 1920, 'height': 1080},
#                 user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
#             )
#             page = context.new_page()
            
#             page.goto(url, wait_until='domcontentloaded', timeout=timeout * 1000)
#             time.sleep(3)
            
#             # Scroll to load images and details
#             for i in range(3):
#                 page.evaluate(f'window.scrollBy(0, {500 + i * 200})')
#                 time.sleep(0.3)
            
#             html = page.content()
#             browser.close()
            
#             return html
            
#     except Exception as e:
#         print(f"   ⚠️ Scrape failed: {str(e)[:50]}")
#         return None


# def scrape_multiple_products(urls: List[Dict[str, str]], max_workers: int = 15) -> List[Dict[str, str]]:
#     """Scrape multiple product pages in parallel"""
#     print(f"\n⚡ Scraping {len(urls)} product pages (workers: {max_workers})...")
    
#     results = []
    
#     with ThreadPoolExecutor(max_workers=max_workers) as executor:
#         future_to_url = {executor.submit(scrape_product_page, item['url']): item for item in urls}
        
#         for idx, future in enumerate(as_completed(future_to_url), 1):
#             item = future_to_url[future]
#             try:
#                 html = future.result()
#                 if html:
#                     results.append({
#                         'url': item['url'],
#                         'title': item['title'],
#                         'html': html
#                     })
#                     print(f"   ✅ {idx}/{len(urls)}")
#                 else:
#                     print(f"   ⚠️ {idx}/{len(urls)} - No HTML returned")
#             except Exception as e:
#                 print(f"   ❌ {idx}/{len(urls)} - {str(e)[:50]}")
    
#     print(f"✅ Scraped: {len(results)}/{len(urls)} pages")
#     return results


# # ============================================================================
# # STEP 3: EXTRACT WITH AI (FILTER MATCHING)
# # ============================================================================

# def clean_html(html: str) -> str:
#     """Clean HTML for AI"""
#     soup = BeautifulSoup(html, 'html.parser')
    
# #     for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'iframe', 'svg']):
# #         tag.decompose()
    
#     product_sections = soup.find_all(['div', 'article'], class_=lambda x: x and any(
#         k in str(x).lower() for k in ['product', 'detail', 'info', 'item']
#     ))
    
#     cleaned = '\n'.join([str(s) for s in product_sections[:50]]) if product_sections else str(soup.find('body') or soup)
#     return cleaned[:80000]

# def extract_price_from_text(text: str) -> float:
#     """Extract numeric price from text with currency symbols"""
#     if not text:
#         return 0.0
    
#     try:
#         # Remove currency symbols and common text
#         text = str(text).replace('₹', '').replace('Rs', '').replace('INR', '')
#         text = text.replace(',', '').replace(' ', '').strip()
        
#         # Extract first number found
#         import re
#         match = re.search(r'\d+\.?\d*', text)
#         if match:
#             return float(match.group())
#         return 0.0
#     except:
#         return 0.0

# def extract_product_with_filters(html: str, url: str, title: str, filters: ProductFilters) -> Optional[Dict]:
#     """Extract product and validate against filters"""
    
# #     cleaned_html = clean_html(html)
    
#     # Build filter criteria
#     brands = filters.brand or []
#     sizes = filters.size or []
#     colors = filters.color or []
#     genders = filters.gender or []
#     category = filters.category or ''
    
#     brands_str = ', '.join(brands) if brands else 'any brand'
#     sizes_str = ', '.join(sizes) if sizes else 'any size'
#     colors_str = ', '.join(colors) if colors else 'any color'
#     genders_str = ', '.join(genders) if genders else 'any gender'
    

#     price_range_str = ""
#     if filters.price_range:
#         min_p = filters.price_range.min or 0
#         max_p = filters.price_range.max or "any"
#         price_range_str = f"\n    - Price Range: ₹{min_p} to ₹{max_p}"
    
#     prompt = f"""
# Extract product from this e-commerce page.

# # URL: {url}

    
# FILTERS TO MATCH:
#     - Brand: One of {brands_str}
#     - Size: Must have size {sizes_str} OR "All Sizes" OR size range including these
#     - Color: {colors_str} (FLEXIBLE - match "Black", "Noir", "Negro", "Dark" for Black)
#     - Gender: {genders_str}
#     - Category: {category if category else 'footwear/slippers/shoes'}{price_range_str}

# HTML (first 60000 chars):
# {cleaned_html[:60000]}

# MATCHING RULES:
# 1. Brand: FLEXIBLE - "Nike", "NIKE", "nike" all match
# 2. Size: If product shows "9 UK" or "Size 9" or "All sizes available" → ACCEPT
# 3. Color: FLEXIBLE - For Black accept: "Black", "Noir", "Negro", "Dark", "Onyx"
# 4. Stock Status Detection (CRITICAL):
#    - If "Add to Cart" OR "Buy Now" OR "Add to Bag" button exists → in_stock = true, availability_status = "in_stock"
#    - If "Out of Stock" OR "Currently Unavailable" OR "Notify Me" → in_stock = false, availability_status = "out_of_stock"
#    - If "Only X left" OR "Limited Stock" → in_stock = true, availability_status = "limited_stock"
#    - DEFAULT to in_stock = true if no clear unavailability message found
# 5. DO NOT reject out of stock products - include them with correct status

# Extract ALL product details visible on page.

# Return JSON:
# {{
#     "name": "Full product name",
#     "brand": "Nike",
#     "price": "1299" or "₹1,299" or "Rs. 1299.00",
#     "original_price": "1999" or "₹1,999" or "Rs. 1999.00",
#     "discount": 35,
#     "image_url": "https://image-url.jpg",
#     "product_url": "{url}",
#     "rating": 4.3,
#     "reviews": 567,
#     "gender": "Men",
#     "size": "9 or size range",
#     "colour": "Black",
#     "in_stock": true,
#     "availability_status": "in_stock",
#     "is_trending": false,
#     "category": "slippers"
# }}

# Return null ONLY if:
# - Completely wrong brand (not {brands_str})
# - Wrong category (shoes when searching slippers)
# - Page is not a product page

# CRITICAL: NEVER return null for out-of-stock products. ALWAYS extract them with:
# - in_stock: false
# - availability_status: "out_of_stock"

# Be FLEXIBLE with size and color matching. Extract ALL products regardless of stock status.
# """
    
#     try:
#         response = openai.chat.completions.create(
#             model="gpt-4o-mini",
#             messages=[
#                 {"role": "system", "content": "Extract product even if out of stock. Return JSON or null only if completely irrelevant."},
#                 {"role": "user", "content": prompt}
#             ],
#             temperature=0.1,
#             max_tokens=1000
#         )
        
# #         ai_output = response.choices[0].message.content.strip()
# #         ai_output = ai_output.replace('```json', '').replace('```', '').strip()
        
# #         if ai_output.lower() == 'null' or not ai_output:
# #             return None
        
# #         product = json.loads(ai_output)
        
#         # More lenient validation - don't drop products easily
#         # Validate brand (more flexible)
#         if brands:
#             product_brand = str(product.get('brand', '')).lower()
#             product_name = str(product.get('name', '')).lower()
#             brand_match = any(
#                 b.lower() in product_brand or b.lower() in product_name 
#                 for b in brands
#             )
#             if not brand_match:
#                 print(f"   ⚠️ Brand mismatch: {product.get('brand')} not in {brands}")
#                 return None
            
#         # Fix stock status - default to true if not explicitly false
#         if 'in_stock' not in product or product.get('in_stock') is None:
#             product['in_stock'] = True
#             print(f"   ℹ️ Stock status not found, defaulting to in_stock=True")
        
#         # Ensure boolean type
#         product['in_stock'] = bool(product.get('in_stock', True))

#         # Size validation - accept if size mentioned anywhere
#         if sizes:
#             product_size = str(product.get('size', '')).lower()
#             # Accept if any filter size is mentioned, or "all sizes"
#             if 'all' not in product_size:
#                 size_match = any(s.lower() in product_size for s in sizes)
#                 if not size_match:
#                     print(f"   ℹ️ Size mismatch: {product.get('size')} not matching {sizes}")
#                     # Don't reject, just log

#         # Color validation - flexible matching
#         if colors:
#             product_color = str(product.get('colour', '')).lower()
#             # Flexible color matching
#             color_variants = {
#                 'black': ['black', 'noir', 'negro', 'dark', 'onyx'],
#                 'white': ['white', 'blanc', 'blanco', 'off-white'],
#                 'blue': ['blue', 'bleu', 'azul', 'navy'],
#                 'red': ['red', 'rouge', 'rojo', 'maroon'],
#                 'grey': ['grey', 'gray', 'gris', 'silver'],
#                 'brown': ['brown', 'tan', 'beige', 'marron']
#             }
            
#             color_match = False
#             for filter_color in colors:
#                 fc_lower = filter_color.lower()
#                 variants = color_variants.get(fc_lower, [fc_lower])
#                 if any(v in product_color for v in variants):
#                     color_match = True
#                     break
            
#             if not color_match:
#                 print(f"   ℹ️ Color mismatch: {product.get('colour')} not matching {colors}")
#                 # Don't reject, just log
        
#           # Normalize prices - extract numbers from text FIRST
#         if 'price' in product:
#             product['price'] = extract_price_from_text(product.get('price', 0))
        
#         if 'original_price' in product:
#             product['original_price'] = extract_price_from_text(product.get('original_price', 0))
        
#         # Log stock status for debugging
#         stock_status = product.get('in_stock', True)
#         availability = product.get('availability_status', 'unknown')
#         print(f"   📦 Stock: in_stock={stock_status}, status={availability}")
        
#         # Price range validation AFTER normalization
#         if filters.price_range:
#             product_price = float(product.get('price', 0))
#             min_price = filters.price_range.min or 0
#             max_price = filters.price_range.max
            
#             if product_price < min_price:
#                 print(f"   ℹ️ Price too low: ₹{product_price} < ₹{min_price}")
#                 return None
            
#             if max_price and product_price > max_price:
#                 print(f"   ℹ️ Price too high: ₹{product_price} > ₹{max_price}")
#                 return None
        
#         # NOW validate price range with numeric values
#         if filters.price_range:
#             product_price = product.get('price', 0)
#             min_price = filters.price_range.min or 0
#             max_price = filters.price_range.max
            
#             if product_price < min_price:
#                 print(f"   ℹ️ Price too low: ₹{product_price} < ₹{min_price}")
#                 return None
            
#             if max_price and product_price > max_price:
#                 print(f"   ℹ️ Price too high: ₹{product_price} > ₹{max_price}")
#                 return None
        
#         # Set availability_status if not present
#         if 'availability_status' not in product:
#             product['availability_status'] = "in_stock" if product.get('in_stock', True) else "out_of_stock"
        
#         return product
        
#     except Exception as e:
#         print(f"   ⚠️ AI Error: {e}")
#         return None


# def extract_products_batch(scraped_pages: List[Dict], filters: ProductFilters, batch_size: int = 10) -> List[Dict]:
#     """Process products in batches to reduce latency"""
#     print(f"\n🤖 Extracting products in batches of {batch_size}...")
    
# #     all_products = []
# #     total = len(scraped_pages)
    
#     for batch_start in range(0, total, batch_size):
#         batch_end = min(batch_start + batch_size, total)
#         batch = scraped_pages[batch_start:batch_end]
        
#         print(f"\n   Batch {batch_start//batch_size + 1} ({batch_start+1}-{batch_end}/{total})...")
        
#         # Process batch in parallel with ThreadPoolExecutor
#         with ThreadPoolExecutor(max_workers=5) as executor:
#             futures = {
#                 executor.submit(
#                     extract_product_with_filters,
#                     page['html'],
#                     page['url'],
#                     page['title'],
#                     filters
#                 ): page for page in batch
#             }
            
#             for future in as_completed(futures):
#                 try:
#                     product = future.result(timeout=15)
#                     if product:
#                         all_products.append(product)
#                         status = product.get('availability_status', 'unknown')
#                         print(f"      ✅ Match: {product['name'][:40]} [{status}]")
#                 except Exception as e:
#                     print(f"      ⚠️ Error: {str(e)[:50]}")
        
#         # Continue processing all batches - don't exit early
    
#     return all_products


# # # ============================================================================
# # # STEP 4: ENHANCE & SORT
# # # ============================================================================

# def fix_amazon_image_url(url: str) -> str:
#     """Fix Amazon image URLs with special characters"""
#     if not url or 'amazon' not in url.lower():
#         return url
    
#     try:
#         # Decode if already encoded
#         decoded = unquote(url)
#         # Re-encode properly
#         parts = decoded.split('/')
#         encoded_parts = [quote(part, safe=':?=&') if i > 2 else part for i, part in enumerate(parts)]
#         fixed_url = '/'.join(encoded_parts)
#         return fixed_url
#     except:
#         return url


# def classify_product(product: Dict) -> str:
#     """Classify product as trending, top_selling, or normal"""
#     rating = product.get('rating', 0)
#     reviews = product.get('reviews', 0)
#     discount = product.get('discount', 0)
    
#     # Trending: High discount + decent rating
#     if discount >= 30 and rating >= 4.0:
#         return ProductCategory.TRENDING.value
    
#     # Top Selling: High reviews + high rating
#     if reviews >= 500 and rating >= 4.2:
#         return ProductCategory.TOP_SELLING.value
    
#     return ProductCategory.NORMAL.value


# def deduplicate_products(products: List[Dict]) -> List[Dict]:
#     """Remove duplicates by URL and normalized name"""
#     seen_urls = set()
#     seen_names = set()
#     unique = []
    
#     for p in products:
#         url = p.get('product_url', '')
        
#         # Primary deduplication by URL
#         if url and url != '#' and url in seen_urls:
#             continue
        
#         # Secondary deduplication by normalized name
#         name = p.get('name', '').lower().strip()
#         name = re.sub(r'\s+', ' ', name)  # Normalize whitespace
#         name = re.sub(r'[^\w\s]', '', name)  # Remove special chars
#         name_key = name[:50]
        
#         if name_key and name_key in seen_names:
#             continue
        
#         # Add to unique list
#         if url and url != '#':
#             seen_urls.add(url)
#         if name_key:
#             seen_names.add(name_key)
        
#         unique.append(p)
    
#     print(f"   🔄 Deduplication: {len(products)} → {len(unique)} products")
#     return unique


# def enhance_and_sort(products: List[Dict], website: str) -> List[Product]:
#     """Add metadata, classify, and sort by relevance"""
    
#     products = deduplicate_products(products)
    
#     enhanced_products = []
    
#     for idx, p in enumerate(products):
#         # Add metadata
#         p['id'] = f"prod_{idx + 1:04d}"
#         p['scraped_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
#         p['currency'] = 'INR'
#         p['source_website'] = website
        
#         # Defaults
#         p.setdefault('name', 'Unknown Product')
#         p.setdefault('brand', 'Unknown')
#         p.setdefault('gender', 'Unknown')
#         p.setdefault('size', 'Unknown')
#         p.setdefault('colour', 'Unknown')
#         p.setdefault('category', 'footwear')
        
#         # Type conversions with error handling
#         try:
#             p['price'] = float(p.get('price', 0) or 0)
#             p['original_price'] = float(p.get('original_price', p['price']) or p['price'])
#             p['discount'] = int(p.get('discount', 0) or 0)
#             p['rating'] = float(p.get('rating', 0) or 0)
#             p['reviews'] = int(p.get('reviews', 0) or 0)
#         except:
#             pass
        
#         p['in_stock'] = bool(p.get('in_stock', True))
#         p['is_trending'] = bool(p.get('is_trending', False))
        
#         # Fix Amazon image URLs
#         image_url = p.get('image_url', '')
#         if 'amazon' in website.lower() and image_url:
#             p['image_url'] = fix_amazon_image_url(image_url)
        
#         # Validate URLs
#         if not image_url or not image_url.startswith('http'):
#             p['image_url'] = 'https://via.placeholder.com/600x600?text=No+Image'
        
#         product_url = p.get('product_url', '')
#         if not product_url or not product_url.startswith('http'):
#             p['product_url'] = '#'
        
#         # Savings
#         try:
#             if p['original_price'] > p['price'] > 0:
#                 p['savings'] = round(p['original_price'] - p['price'], 2)
#             else:
#                 p['savings'] = 0.0
#         except:
#             p['savings'] = 0.0
        
#         # Classify product
#         p['product_classification'] = classify_product(p)
        
#         # Set availability status
#         if 'availability_status' not in p:
#             p['availability_status'] = "in_stock" if p['in_stock'] else "out_of_stock"
        
#         # Create Pydantic model (will use defaults for missing fields)
#         try:
#             product_model = Product(**p)
#             enhanced_products.append(product_model)
#         except Exception as e:
#             print(f"   ⚠️ Product validation error: {str(e)[:100]}")
#             # Still try to include with minimal data
#             try:
#                 minimal_product = Product(
#                     name=p.get('name', 'Unknown'),
#                     brand=p.get('brand', 'Unknown'),
#                     price=p.get('price', 0),
#                     product_url=p.get('product_url', '#'),
#                     image_url=p.get('image_url', 'https://via.placeholder.com/600x600?text=No+Image')
#                 )
#                 enhanced_products.append(minimal_product)
#             except:
#                 print(f"   ❌ Failed to include product")
    
# # Sort: In-Stock First → Trending → Top Selling → Rating → Reviews → Discount
#     enhanced_products.sort(key=lambda x: (
#         not x.in_stock,  # In-stock products first
#         x.product_classification != ProductCategory.TRENDING.value,
#         x.product_classification != ProductCategory.TOP_SELLING.value,
#         -x.rating,
#         -x.reviews,
#         -x.discount
#     ))
    
#     in_stock_count = sum(1 for p in enhanced_products if p.in_stock)
#     out_of_stock_count = len(enhanced_products) - in_stock_count
#     print(f"   📊 Sorted: {in_stock_count} in-stock, {out_of_stock_count} out-of-stock")
    
#     return enhanced_products


# # ============================================================================
# # MAIN SCRAPING ORCHESTRATOR
# # ============================================================================

# def scrape_products(website: str, filters: ProductFilters, max_results: int = 50) -> List[Product]:
#     """
#     Main orchestrator for product scraping
    
#     Args:
#         website: Website to scrape
#         filters: Product filters
#         max_results: Maximum number of product URLs to fetch
    
#     Returns:
#         List of Product models
#     """
#     print(f"\n{'='*70}")
#     print(f"🎯 STARTING SCRAPE")
#     print(f"{'='*70}")
#     print(f"Website: {website}")
#     print(f"Filters: {filters.dict()}")
#     print(f"Max Results: {max_results}")
    
#     # STEP 1: Build search query
#     query = build_search_query(filters)
    
#     # STEP 2: Search product URLs
#     product_urls = search_product_urls(query, website, max_results=max_results)
    
#     if not product_urls:
#         print("❌ No product URLs found")
#         return []
    
#     # STEP 3: Scrape product pages (limit to max_results to avoid excessive scraping)
#     urls_to_scrape = product_urls[:min(len(product_urls), max_results)]
#     scraped_pages = scrape_multiple_products(urls_to_scrape, max_workers=15)
    
#     if not scraped_pages:
#         print("❌ No pages scraped successfully")
#         return []
    
#     # STEP 4: Extract with filter matching
#     raw_products = extract_products_batch(scraped_pages, filters, batch_size=10)
    
#  # STEP 5: Enhance, classify, and sort
#     products = enhance_and_sort(raw_products, website)
    
#     # STEP 6: Prioritize in-stock products
#     in_stock_products = [p for p in products if p.in_stock]
#     out_of_stock_products = [p for p in products if not p.in_stock]
    
#     # If we have enough in-stock products, limit out-of-stock to 20%
#     if len(in_stock_products) >= 10:
#         max_out_of_stock = max(5, int(len(in_stock_products) * 0.2))
#         out_of_stock_products = out_of_stock_products[:max_out_of_stock]
#         print(f"   🎯 Filtered: {len(in_stock_products)} in-stock + {len(out_of_stock_products)} out-of-stock")
#     else:
#         print(f"   ℹ️ Limited in-stock ({len(in_stock_products)}), including all {len(out_of_stock_products)} out-of-stock")
    
#     products = in_stock_products + out_of_stock_products
    
#     print(f"\n✅ SUCCESS! Returning {len(products)} products")
#     print(f"   📊 In-stock: {len(in_stock_products)}, Out-of-stock: {len(out_of_stock_products)}")
#     print(f"{'='*70}\n")
    
#     return products