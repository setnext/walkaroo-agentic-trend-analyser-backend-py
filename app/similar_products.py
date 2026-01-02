import os
import requests
from dotenv import load_dotenv
import boto3
import uuid
load_dotenv()

class ImageSearchService:
    def __init__(self):

        
        print("Initialized ImageSearchService with SERPAPI key:", self.SEARCH_API_KEY, self.SEARCH_URL)

    
    def upload_to_s3(self, image_bytes: bytes, filename: str) -> str:
        key = f"uploads/{uuid.uuid4()}-{filename}"

        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=image_bytes,
            ContentType="image/jpeg",
            ACL="public-read"
        )

        return f"https://{self.bucket}.s3.amazonaws.com/{key}"


    def search_similar_images(self, image_bytes: bytes,filename):
        image_url = self.upload_to_s3(image_bytes, filename)

        # Parameters for Google Lens engine
        params = {
            "engine": "google_lens",
            "url": image_url,
            "api_key": self.SEARCH_API_KEY,
            "search_type": "visual_matches" ,
            "country": "in"
        }

        # The missing Endpoint URL
        url = "https://www.searchapi.io/api/v1/search"

        # Make the request
        response = requests.get(url, params=params)
        data = response.json()

        print("dataaa",data)

        products = []

        for item in data["visual_matches"]:
            products.append({
                "title": item.get("title"),
                "image": item.get("image", {}).get("link") or item.get("thumbnail"),
                "price": item.get("price"),
                "rating": item.get("rating"),
                "reviews": item.get("reviews"),
                "store": item.get("source"),
                "url": item.get("link")
            })
        print("productsssss",products)
        return products


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
    


