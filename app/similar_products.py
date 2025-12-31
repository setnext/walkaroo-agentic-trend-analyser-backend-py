import os
import requests
from dotenv import load_dotenv
import boto3
import uuid
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

load_dotenv()

class ImageSearchService:
    def __init__(self):
        # Load environment variables
        self.SEARCH_API_KEY = os.getenv("SEARCH_API_KEY")
        self.SEARCH_URL = "https://www.searchapi.io/api/v1/search"
        
        # AWS S3 Configuration
        self.bucket = os.getenv("AWS_BUCKET_NAME")
        self.s3 = boto3.client(
            's3',
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION", "us-east-1")
        )
        
        print("Initialized ImageSearchService with SERPAPI key:", self.SEARCH_API_KEY)

    
    def upload_to_s3(self, image_bytes: bytes, filename: str) -> str:
        """Upload image to S3 and return public URL"""
        try:
            key = f"uploads/{uuid.uuid4()}-{filename}"

            self.s3.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=image_bytes,
                ContentType="image/jpeg",
                ACL="public-read"
            )

            url = f"https://{self.bucket}.s3.amazonaws.com/{key}"
            print(f"Uploaded to S3: {url}")
            return url
            
        except Exception as e:
            print(f"S3 upload error: {e}")
            raise


    def search_similar_images(self, image_bytes: bytes, filename: str):
        """Search for similar images using Google Lens API"""
        try:
            # Upload to S3 first
            image_url = self.upload_to_s3(image_bytes, filename)

            # Parameters for Google Lens engine
            params = {
                "engine": "google_lens",
                "url": image_url,
                "api_key": self.SEARCH_API_KEY,
                "search_type": "visual_matches",
                "country": "in"
            }

            # Make the request
            print(f"Searching with URL: {image_url}")
            response = requests.get(self.SEARCH_URL, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            print("API Response:", data)

            # Check if visual_matches exists
            if "visual_matches" not in data:
                print("Warning: No 'visual_matches' in response")
                print("Available keys:", data.keys())
                return []

            products = []

            for item in data.get("visual_matches", []):
                # Safely extract image URL
                image_data = item.get("image", {})
                if isinstance(image_data, dict):
                    image_link = image_data.get("link")
                else:
                    image_link = None
                
                # Fallback to thumbnail if no image link
                final_image = image_link or item.get("thumbnail", "")
                
                product = {
                    "title": item.get("title", "Unknown Product"),
                    "image": final_image,
                    "price": item.get("price"),
                    "rating": item.get("rating"),
                    "reviews": item.get("reviews"),
                    "store": item.get("source"),
                    "url": item.get("link")
                }
                
                products.append(product)
            
            print(f"Found {len(products)} products")
            return products
            
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            raise
        except Exception as e:
            print(f"Error in search_similar_images: {e}")
            import traceback
            traceback.print_exc()
            raise


# FastAPI Application
app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Add your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize service
search_service = ImageSearchService()


@app.get("/")
async def root():
    return {"message": "Image Search API is running"}


@app.post("/similar-products")
async def similar_products(file: UploadFile = File(...)):
    """
    Upload an image and get similar product results
    """
    try:
        # Validate file
        if not file.content_type.startswith('image/'):
            return JSONResponse(
                status_code=400,
                content={
                    "error": "File must be an image",
                    "results": [],
                    "success": False
                }
            )
        
        # Read file content
        contents = await file.read()
        print(f"Received file: {file.filename}, size: {len(contents)} bytes")
        
        # Search for similar images
        results = search_service.search_similar_images(contents, file.filename)
        
        return {
            "results": results,
            "success": True,
            "count": len(results)
        }
        
    except Exception as e:
        print(f"Error in similar-products endpoint: {e}")
        import traceback
        traceback.print_exc()
        
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "results": [],
                "success": False
            }
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


# import base64
# import json
# from openai import OpenAI
# import requests
# from dotenv import load_dotenv
# load_dotenv()
# import os


# # GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")




# class ImageSearchService:
#     def __init__(self):
#         self.client = OpenAI(api_key=os.getenv("OPENAI"))
#         self.SEARCH_API_KEY = os.getenv("SEARCH_API_KEY")
#         self.SEARCH_URL = os.getenv("SEARCH_URL")

#         print("Initialized ImageSearchService with OpenAI and SERPAPI keys::", self.SEARCH_API_KEY)
    
#     def search_similar_images(self, image_url):    

        
#         # Parameters for Google Lens engine
#         params = {
#             "engine": "google_lens",
#             "url": image_url,
#             "api_key": self.SEARCH_API_KEY,
#             "search_type": "visual_matches"  # Focuses results on similar images
#         }


#         # Make the request
#         response = requests.get(self.SEARCH_URL, params=params)
#         data = response.json()

#         # Print Similar Images and their source links
#         if "visual_matches" in data:
#             print(f"Found {len(data['visual_matches'])} visual matches:")
#             for match in data["visual_matches"]:
#                 print(f"Title: {match.get('title')}")
#                 print(f"Source Link: {match.get('link')}")     # Web page link
#                 print(f"Image Link: {match.get('thumbnail')}")  # Image file link
#                 print("-" * 20)
#         else:
#             print("No matches found or check API balance.")

    # # ------------------ Encode Image ------------------
    # def image_to_base64(self, image_bytes: bytes) -> str:
    #     return base64.b64encode(image_bytes).decode("utf-8")


    # # ------------------ Image → Description ------------------
    # def get_image_description(self, image_bytes: bytes):
    #     image_base64 = self.image_to_base64(image_bytes)

    #     response = self.client.chat.completions.create(
    #         model="gpt-4.1",
    #         messages=[
    #             {
    #                 "role": "user",
    #                 "content": [
    #                     {"type": "text",
    #         "text": 
    #         """You are a footwear expert. Analyze the image and describe the footwear and its in a concise, search-optimized way.

    #         Return ONLY valid JSON with the following fields:
    #         - footwear_type
    #         - material
    #         - sole_type
    #         - style
    #         - gender
    #         - short_search_description"""       },
    #                     {
    #                         "type": "image_url",
    #                         "image_url": {
    #                             "url": f"data:image/jpeg;base64,{image_base64}"
    #                         }
    #                     }
    #                 ]
    #             }
    #         ],
    #         max_tokens=100
    #     )

    #     print(response.choices[0].message.content)
    #     raw = (response.choices[0].message.content)
    #     clean = raw.replace("```json", "").replace("```", "").strip()

    #     # Convert to dict
    #     return json.loads(clean)


    # def serpapi_search(self, image_path):
    #     print("Searching similar products for image:", image_path)
    #     query = self.get_image_description(image_path)
    #     print("Generated query:", query)
    #     short_search_description = query['short_search_description']
    #     print("short_search_description ::: ", short_search_description)
    #     params = {
    #         "engine": "google_images",
    #         "q": short_search_description,
    #         "api_key": self.SERP_API_KEY,
    #         "num": 10
    #     }

    #     response = requests.get("https://serpapi.com/search", params=params)
    #     data = response.json()
    #     print("data", len(data))    
    #     # print("dataaa", (data["images_results"]["original"]))
    #     original_urls = [item["original"] for item in data["images_results"]]
    #     print("original_urls", (original_urls))
    #     return original_urls
    


