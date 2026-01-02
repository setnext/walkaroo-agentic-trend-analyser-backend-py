# # ============================================================================
# # OPTIMIZED scraper.py - LOW LATENCY VERSION
# # Key improvements:
# # 1. Aggressive timeouts (10s max per page)
# # 2. Concurrent batch processing
# # 3. Early termination when enough products found
# # 4. Smart fallback strategy
# # ============================================================================

# from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
# from bs4 import BeautifulSoup
# import json
# import os
# import time
# import requests
# from dotenv import load_dotenv
# from openai import OpenAI
# from concurrent.futures import ThreadPoolExecutor, as_completed
# import re
# from typing import List, Dict, Optional, Any
# import asyncio

# # Load environment variables
# load_dotenv()
# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
# GOOGLE_CX = os.getenv('GOOGLE_CX')

# # Website configurations
# WEBSITES = {
#     'flipkart': {'base': 'https://www.flipkart.com/search?q=', 'domain': 'flipkart.com'},
#     'reliancedigital': {'base': 'https://www.reliancedigital.in/search?q=', 'domain': 'reliancedigital.in'},
#     'myntra': {'base': 'https://www.myntra.com/', 'domain': 'myntra.com'},
#     'amazon': {'base': 'https://www.amazon.in/s?k=', 'domain': 'amazon.in'}
# }

# # ============================================================================
# # STEP 1: BUILD SEARCH QUERY & FIND PRODUCT URLS
# # ============================================================================

# def build_search_query(filters: Dict[str, Any]) -> str:
#     """Build optimized search query from filters"""
#     parts = []
    
#     if filters.get('brand'):
#         parts.extend(filters['brand'])
#     if filters.get('category'):
#         parts.append(filters['category'])
#     if filters.get('gender'):
#         parts.extend([g.lower() for g in filters['gender']])
#     if filters.get('color') and len(filters['color']) <= 3:
#         parts.extend([c.lower() for c in filters['color']])
    
#     query = ' '.join(parts)
#     print(f"🔍 Search Query: {query}")
#     return query


# def is_product_page(url: str, domain: str) -> bool:
#     """Check if URL is an actual product page"""
#     url_lower = url.lower()
    
#     skip_patterns = [
#         '/search?', '/s?k=', '/brand/', '/pr?sid=', '/collection/',
#         '/shop/', '/store/', '/help/', '/about', '/contact'
#     ]
    
#     if any(p in url_lower for p in skip_patterns):
#         return False
    
#     if 'flipkart.com' in domain:
#         return '/p/' in url_lower or '/itm/' in url_lower
#     elif 'amazon.in' in domain:
#         return '/dp/' in url_lower or '/gp/product/' in url_lower
#     elif 'myntra.com' in domain:
#         return re.search(r'/\d+/buy', url_lower) is not None
    
#     return len(url) > 50


# def search_product_urls(query: str, website: str, max_results: int = 30) -> List[Dict[str, str]]:
#     """Search Google for PRODUCT pages only - REDUCED MAX RESULTS"""
#     if not GOOGLE_API_KEY or not GOOGLE_CX:
#         print("❌ Google API not configured!")
#         return []
    
#     print(f"\n🔍 Searching Google: '{query}' on {website}")
    
#     website_config = WEBSITES.get(website.lower(), WEBSITES['flipkart'])
#     site_domain = website_config['domain']
    
#     all_urls = []
#     # Reduced to 3 requests max (30 URLs)
#     num_requests = min((max_results + 9) // 10, 3)
    
#     for start_index in range(1, num_requests * 10 + 1, 10):
#         try:
#             params = {
#                 'key': GOOGLE_API_KEY,
#                 'cx': GOOGLE_CX,
#                 'q': f'{query} site:{site_domain}',
#                 'start': start_index,
#                 'num': 10,
#                 'gl': 'in',
#                 'hl': 'en'
#             }
            
#             response = requests.get(
#                 'https://www.googleapis.com/customsearch/v1',
#                 params=params,
#                 timeout=5  # Reduced timeout
#             )
            
#             if response.status_code != 200:
#                 break
            
#             data = response.json()
#             if 'items' not in data:
#                 break
            
#             for item in data['items']:
#                 url = item.get('link', '')
#                 title = item.get('title', '')
                
#                 if is_product_page(url, site_domain):
#                     all_urls.append({'url': url, 'title': title})
            
#             print(f"   Found: {len(all_urls)} product URLs")
#             time.sleep(0.3)  # Reduced delay
            
#         except Exception as e:
#             print(f"❌ Search Error: {e}")
#             break
    
#     print(f"✅ Total Product URLs: {len(all_urls)}")
#     return all_urls


# # ============================================================================
# # STEP 2: OPTIMIZED SCRAPING WITH AGGRESSIVE TIMEOUTS
# # ============================================================================

# def scrape_product_page_simple(url: str, timeout: int = 8) -> Optional[str]:
#     """Fast fallback scraper using requests"""
#     try:
#         headers = {
#             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
#             'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#         }
        
#         response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
#         response.raise_for_status()
#         return response.text
            
#     except Exception:
#         return None


# async def scrape_single_page_fast(url: str, use_playwright: bool = True) -> Optional[str]:
#     """
#     ULTRA-FAST single page scraper with aggressive timeout
#     Max 10 seconds per page, no retries
#     """
#     if not use_playwright:
#         return scrape_product_page_simple(url, timeout=8)

#     try:
#         async with async_playwright() as p:
#             browser = await p.chromium.launch(
#                 headless=True,
#                 args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
#             )

#             page = await browser.new_page()
            
#             # AGGRESSIVE TIMEOUT: 10 seconds max
#             await page.goto(url, wait_until="domcontentloaded", timeout=10000)
            
#             # Minimal wait - just 1 second
#             await page.wait_for_timeout(1000)
            
#             # Quick scroll (2 times only)
#             for _ in range(2):
#                 await page.mouse.wheel(0, 800)
#                 await page.wait_for_timeout(300)
            
#             html = await page.content()
#             await browser.close()
            
#             return html

#     except PlaywrightTimeout:
#         # Immediately fallback to simple scraper
#         return scrape_product_page_simple(url, timeout=5)
        
#     except Exception:
#         return scrape_product_page_simple(url, timeout=5)


# async def scrape_multiple_products_optimized(
#     urls: List[Dict[str, str]], 
#     max_concurrent: int = 8
# ) -> List[Dict[str, str]]:
#     """
#     Optimized parallel scraping with:
#     - Semaphore to limit concurrent requests
#     - Early termination when we have enough results
#     - Smart batching
#     """
#     print(f"\n🚀 Scraping {len(urls)} URLs (max {max_concurrent} concurrent)...")
    
#     semaphore = asyncio.Semaphore(max_concurrent)
#     results = []
    
#     async def scrape_with_semaphore(item):
#         async with semaphore:
#             html = await scrape_single_page_fast(item['url'], use_playwright=True)
#             if html:
#                 return {'url': item['url'], 'title': item['title'], 'html': html}
#             return None
    
#     # Process all URLs concurrently (limited by semaphore)
#     tasks = [scrape_with_semaphore(item) for item in urls]
    
#     # Use as_completed to process results as they arrive
#     for coro in asyncio.as_completed(tasks):
#         result = await coro
#         if result:
#             results.append(result)
#             print(f"   ✅ {len(results)}/{len(urls)} scraped")
            
#             # Early termination if we have enough
#             if len(results) >= 25:
#                 print(f"   🎯 Got {len(results)} pages, stopping early")
#                 break
    
#     return results


# # ============================================================================
# # STEP 3: EXTRACT WITH AI (OPTIMIZED PROMPTS)
# # ============================================================================

# def clean_html(html: str) -> str:
#     """Fast HTML cleaning"""
#     soup = BeautifulSoup(html, 'html.parser')
    
#     for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'iframe', 'svg']):
#         tag.decompose()
    
#     # Quick extraction - just body
#     body = soup.find('body')
#     cleaned = str(body) if body else str(soup)
    
#     # Aggressive truncation for speed
#     return cleaned[:60000]


# def extract_product_with_filters(
#     html: str, 
#     url: str, 
#     title: str, 
#     filters: Dict[str, Any]
# ) -> Optional[Dict[str, Any]]:
#     """Extract product - NO STRICT FILTERING, get whatever exists"""
    
#     cleaned_html = clean_html(html)
    
#     # Build OPTIONAL filter hints (not requirements)
#     filter_hints = []
#     if filters.get('brand'):
#         filter_hints.append(f"Preferred brands: {', '.join(filters['brand'])}")
#     if filters.get('size'):
#         filter_hints.append(f"Looking for sizes: {', '.join(filters['size'])}")
#     if filters.get('color'):
#         filter_hints.append(f"Preferred colors: {', '.join(filters['color'])}")
#     if filters.get('category'):
#         filter_hints.append(f"Category: {filters['category']}")
    
#     hints_text = '\n'.join(filter_hints) if filter_hints else 'No specific filters'
    
#     # RELAXED PROMPT - extract everything available
#     prompt = f"""Extract ALL product data from this e-commerce page. Get whatever information exists.

# URL: {url}

# USER PREFERENCES (not strict requirements):
# {hints_text}

# HTML:
# {cleaned_html[:50000]}

# INSTRUCTIONS:
# 1. Extract ALL available product details
# 2. If size/color/brand exists, include it
# 3. If size shows "9" or "9 UK" or "Size 9" → set size: "9"
# 4. If multiple sizes available, list them OR set "All sizes available"
# 5. ONLY reject if clearly OUT OF STOCK (shows "Out of Stock", "Currently Unavailable")
# 6. If "Add to Cart" or "Buy Now" exists → in_stock: true

# Return JSON with ALL available data:
# {{
#     "name": "full product name from page",
#     "brand": "Brand name (extract from page)",
#     "price": 1299.0,
#     "original_price": 1999.0,
#     "discount": 35,
#     "image_url": "https://...",
#     "product_url": "{url}",
#     "rating": 4.3,
#     "reviews": 567,
#     "gender": "Men/Women/Unisex/Unknown",
#     "size": "9" or "All sizes" or "8,9,10",
#     "colour": "Black/White/whatever is shown",
#     "in_stock": true,
#     "category": "slippers/shoes/sandals"
# }}

# Return null ONLY if page is completely broken or clearly out of stock."""
    
#     try:
#         response = client.chat.completions.create(
#             model="gpt-4o-mini",
#             messages=[
#                 {"role": "system", "content": "Extract ALL product data available. Be flexible with sizes/colors."},
#                 {"role": "user", "content": prompt}
#             ],
#             temperature=0.1,
#             max_tokens=800
#         )
        
#         ai_output = response.choices[0].message.content.strip()
#         ai_output = ai_output.replace('```json', '').replace('```', '').strip()
        
#         if ai_output.lower() == 'null' or not ai_output:
#             return None
        
#         product = json.loads(ai_output)
        
#         # ONLY reject if clearly out of stock
#         if not product.get('in_stock', True):
#             return None
        
#         return product
        
#     except Exception as e:
#         print(f"   ⚠️ AI Error: {str(e)[:50]}")
#         return None


# def extract_products_parallel(
#     scraped_pages: List[Dict[str, str]], 
#     filters: Dict[str, Any],
#     max_workers: int = 8
# ) -> List[Dict[str, Any]]:
#     """
#     Parallel extraction with early stopping
#     Stop as soon as we have 15-20 good products
#     """
#     print(f"\n🤖 Extracting products with AI (parallel processing)...")
    
#     all_products = []
#     total = len(scraped_pages)
    
#     with ThreadPoolExecutor(max_workers=max_workers) as executor:
#         futures = {
#             executor.submit(
#                 extract_product_with_filters,
#                 page['html'],
#                 page['url'],
#                 page['title'],
#                 filters
#             ): page for page in scraped_pages
#         }
        
#         for future in as_completed(futures):
#             try:
#                 product = future.result(timeout=10)
#                 if product:
#                     all_products.append(product)
#                     print(f"      ✅ Match {len(all_products)}: {product['name'][:40]}")
                    
#                     # Early stopping when we have enough products
#                     if len(all_products) >= 20:
#                         print(f"\n   🎯 Got {len(all_products)} products, stopping extraction...")
                        
#                         # Cancel remaining futures
#                         for f in futures:
#                             f.cancel()
#                         break
                        
#             except Exception as e:
#                 print(f"      ⚠️ Error: {str(e)[:50]}")
    
#     print(f"\n✅ Extracted {len(all_products)} matching products")
#     return all_products


# # ============================================================================
# # STEP 4: ENHANCE & SORT
# # ============================================================================

# def deduplicate_products(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
#     """Remove duplicates based on name, brand, price, and URL"""
#     seen = set()
#     unique = []
    
#     for p in products:
#         name = p.get('name', '').lower().strip()
#         name = re.sub(r'\s+', ' ', name)
#         name = re.sub(r'[^\w\s]', '', name)
        
#         brand = p.get('brand', '').lower().strip()
#         price = str(p.get('price', 0))
#         url = p.get('product_url', '')
        
#         # Create composite key for better deduplication
#         key = (name[:40], brand, price, url)
        
#         if key not in seen and name:
#             seen.add(key)
#             unique.append(p)
#         else:
#             print(f"   🔄 Duplicate removed: {p.get('name', 'Unknown')[:40]}")
    
#     print(f"\n   Removed {len(products) - len(unique)} duplicates")
#     return unique


# def enhance_and_sort(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
#     """Add metadata and sort"""
#     products = deduplicate_products(products)
    
#     for idx, p in enumerate(products):
#         p['id'] = f"prod_{idx + 1:04d}"
#         p['scraped_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
#         p['currency'] = 'INR'
        
#         # Set defaults
#         p.setdefault('name', 'Unknown Product')
#         p.setdefault('brand', 'Unknown')
#         p.setdefault('image_url', 'https://via.placeholder.com/600x600?text=No+Image')
#         p.setdefault('product_url', '#')
        
#         # Type conversions
#         try:
#             p['price'] = float(p.get('price', 0) or 0)
#             p['original_price'] = float(p.get('original_price', p['price']) or p['price'])
#             p['discount'] = int(p.get('discount', 0) or 0)
#             p['rating'] = float(p.get('rating', 0) or 0)
#             p['reviews'] = int(p.get('reviews', 0) or 0)
#         except:
#             pass
    
#     # Sort by trending, rating, reviews, discount
#     products.sort(key=lambda x: (
#         -int(x.get('is_trending', False)),
#         -x.get('rating', 0),
#         -x.get('reviews', 0),
#         -x.get('discount', 0)
#     ))
    
#     return products


# # ============================================================================
# # MAIN OPTIMIZED PIPELINE
# # ============================================================================

# async def scrape_products_pipeline(
#     filters: Dict[str, Any], 
#     website: str = 'flipkart'
# ) -> Dict[str, Any]:
#     """
#     OPTIMIZED scraping pipeline with:
#     - Reduced URL search (30 max)
#     - Aggressive timeouts
#     - Early stopping
#     - Parallel processing
#     """
#     try:
#         start_time = time.time()
        
#         print(f"\n{'='*70}")
#         print(f"🎯 NEW FILTER REQUEST")
#         print(f"{'='*70}")
#         print(f"Website: {website}")
#         print(f"Filters: {json.dumps(filters, indent=2)}")
        
#         # STEP 1: Search (reduced to 30 URLs max)
#         query = build_search_query(filters)
#         product_urls = search_product_urls(query, website, max_results=30)
        
#         if not product_urls:
#             return {
#                 'success': False,
#                 'error': 'No product URLs found',
#                 'filters': filters,
#                 'website': website
#             }
        
#         # STEP 2: Scrape (limit to 25 URLs, parallel with semaphore)
#         product_urls_limited = product_urls[:25]
#         scraped_pages = await scrape_multiple_products_optimized(
#             product_urls_limited, 
#             max_concurrent=8
#         )
        
#         if not scraped_pages:
#             return {
#                 'success': False,
#                 'error': 'Failed to scrape product pages',
#                 'filters': filters,
#                 'website': website
#             }
        
#         # STEP 3: Extract (parallel with early stopping)
#         products = extract_products_parallel(scraped_pages, filters, max_workers=8)
        
#         if not products:
#             return {
#                 'success': False,
#                 'error': 'No products matched the filters',
#                 'filters': filters,
#                 'website': website
#             }
        
#         # STEP 4: Enhance
#         products = enhance_and_sort(products)
        
#         elapsed = time.time() - start_time
        
#         print(f"\n✅ SUCCESS! Returning {len(products)} products")
#         print(f"⏱️  Total time: {elapsed:.1f}s")
#         print(f"{'='*70}\n")
        
#         return {
#             'success': True,
#             'website': website,
#             'filters_applied': filters,
#             'total_products': len(products),
#             'products': products,
#             'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
#             'processing_time_seconds': round(elapsed, 2)
#         }
        
#     except Exception as e:
#         print(f"\n❌ ERROR: {e}")
#         import traceback
#         traceback.print_exc()
        
#         return {
#             'success': False,
#             'error': str(e),
#             'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
#         }


# def check_api_health() -> Dict[str, Any]:
#     """Check API configuration health"""
#     return {
#         'status': 'healthy',
#         'openai_configured': bool(client.api_key),
#         'google_configured': bool(GOOGLE_API_KEY and GOOGLE_CX),
#         'websites': list(WEBSITES.keys())
#     }