import os
import requests
from dotenv import load_dotenv
import boto3
import uuid
from PIL import Image
from openai import OpenAI
from fastapi.responses import StreamingResponse
import io
import base64
import json
import re
load_dotenv()


class BomViewSearchService:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def load_image_for_openai(self, image_path):
        # Open image with Pillow
        img = Image.open(image_path)

        # Convert to RGB (important for some formats)
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")

        # Save to in-memory PNG
        buffer = io.BytesIO()
        # img.save(buffer, format="PNG")
        # buffer.seek(0)

        return buffer  

    def extract_json(text: str) -> dict:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return json.loads(match.group())
            raise ValueError("Invalid JSON returned by model")


    def orthographic_image_generation(self, image_bytes: bytes, filename: str) -> str:
        print("Generating orthographic view for:", filename)
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        # Convert to PNG buffer
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        response = self.client.images.edit(
            model="gpt-image-1",
            image=("filename.png", buffer, "image/png"),
            prompt="""Generate a technical orthographic TOP VIEW of the provided footwear image {image}.

    IMPORTANT INSTRUCTIONS:
    - The output must preserve ALL visible geometric features from the reference image.
    - Do NOT redesign, simplify, or reinterpret the form.
    - Accurately reproduce the exact strap shape, center cutout, buckle position, sole outline, and inner contours.
    - Maintain the same proportions and layout as seen in the source image.
    - This is a trace-style reconstruction, not a conceptual redesign.

    Rendering requirements:
    - Clean black line art on a white background
    - No perspective distortion
    - No shading or textures
    - Uniform technical line weight
    - Suitable for CAD tracing

    This must be a faithful orthographic reproduction of the input image.
    """,
            n=1,
            size="1024x1024"
        )
        image_top_bytes = base64.b64decode(response.data[0].b64_json)
        return image_top_bytes
        # return StreamingResponse(
        # io.BytesIO(image_bytes),
        # media_type="image/png"
    # )
        
    def orthographic_side_image_generation(self, image_bytes: bytes, filename: str) -> str:
            print("Generating side orthographic view for:", filename)
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

            # Convert to PNG buffer
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            buffer.seek(0)
            response = self.client.images.edit(
                model="gpt-image-1",
                image=("filename.png", buffer, "image/png"),
                prompt="""Generate a technical orthographic side view of this {image}. 
                        The drawing should show: - Sole thickness profile - Heel-to-toe drop - Strap height and curvature - Footbed contour Use clean black line art on white background.
                        No perspective, no shading. Engineering-style linework suitable for CAD tracing. """,
                n=1,
                size="1024x1024"
            )

            
            image_side_bytes = base64.b64decode(response.data[0].b64_json)
            print("side view genefrated")
            return image_side_bytes

            # return StreamingResponse(
            #     io.BytesIO(image_bytes),
            #     media_type="image/png")
            
            
    def generate_bom_from_image(self, image_bytes: bytes, filename: str) -> str:
        print("getting into bom")
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        response = self.client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "You are a footwear manufacturing BOM expert. Return ONLY valid JSON."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """
Analyze the product and return BOM JSON:

{
  "product_name": "",
  "components": [
    {
      "name": "",
      "material": "",
      "finish": "",
      "quantity": 1
    }
  ]
}
"""
                    },
                    {
                        "type": "image_url", # 3. Correct type identifier
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}" # 4. Use Data URL format
                            }    }
                ]
            }
        ]
    )
        # 5. Extract JSON safely from standard response object
        output_text = response.choices[0].message.content.strip()
        
        # Optional: Clean markdown if model returns ```json ... ``` blocks
        if output_text.startswith("```json"):
            output_text = output_text.strip("```json").strip("```")
        print("answer:::",json.loads(output_text))
        return json.loads(output_text)