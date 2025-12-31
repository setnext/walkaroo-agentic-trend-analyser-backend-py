from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from dotenv import load_dotenv
from typing import Optional
import base64
import uuid
import json
import re
import os

# =========================================================
# ENV + ROUTER SETUP
# =========================================================
load_dotenv()

router = APIRouter(prefix="/image", tags=["Image Engineering"])

# ✅ Ensure static directory exists BEFORE mounting
STATIC_DIR = "static"
os.makedirs(STATIC_DIR, exist_ok=True)

router.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# =========================================================
# SIZE → SOLE LENGTH (SINGLE SOURCE OF TRUTH)
# =========================================================
SIZE_TO_SOLE_MM = {
    5: 245,
    6: 250,
    7: 255,
    8: 260,
    9: 265,
    10: 270
}

def get_sole_length_from_size(size: int) -> int:
    if size not in SIZE_TO_SOLE_MM:
        raise ValueError("Unsupported size")
    return SIZE_TO_SOLE_MM[size]

# =========================================================
# SAFE JSON EXTRACTION
# =========================================================
def extract_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError("Invalid JSON returned by model")

# =========================================================
# SIZE-AWARE PROMPT
# =========================================================
def build_size_aware_prompt(user_prompt: str, size: int) -> str:
    sole_length = get_sole_length_from_size(size)
    return f"""
{user_prompt}

MANUFACTURING CONSTRAINTS:
- Footwear size: UK/India {size}
- Sole length: {sole_length} mm (PRIMARY SCALE REFERENCE)
- Maintain realistic adult footwear proportions
- Use millimeters only
"""

# =========================================================
# BOM GENERATION
# =========================================================
def generate_bom_from_image(image_bytes: bytes) -> dict:
    response = client.chat.completions.create(
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
                        "type": "image_url",
                        "image_url": {
                            "url": "data:image/png;base64," +
                            base64.b64encode(image_bytes).decode()
                        }
                    }
                ]
            }
        ]
    )
    return extract_json(response.choices[0].message.content)

# =========================================================
# ORTHOGRAPHIC VIEW GENERATION (FROM EDITED IMAGE)
# =========================================================
def generate_single_view(
    edited_image: bytes,
    view_name: str,
    sole_length_mm: int
) -> bytes:

    prompt = f"""
Create a MANUFACTURING-GRADE ORTHOGRAPHIC {view_name.upper()} VIEW.

ABSOLUTE GEOMETRY PRESERVATION (CRITICAL):
- Trace geometry directly from the input image
- Do NOT add, remove, or duplicate features
- Do NOT shift, rotate, scale, or re-center
- Preserve original object placement exactly

PROJECTION:
- Strict orthographic projection only
- No perspective or camera shift

STYLE:
- Black CAD-style linework
- White background
- Uniform line thickness

DIMENSIONING:
- Sole length labeled {sole_length_mm} mm
- Annotate only, do NOT modify geometry
"""

    result = client.images.edit(
        model="gpt-image-1",
        image=[("base.png", edited_image)],
        prompt=prompt,
        size="1024x1024"
    )

    return base64.b64decode(result.data[0].b64_json)

# =========================================================
# MAIN API ENDPOINT
# =========================================================
@router.post("/replace")
async def replace(
    prompt: str = Form(...),
    size: int = Form(...),
    input_image: UploadFile = File(...),
    replace_image: Optional[UploadFile] = File(None),
):
    sole_length_mm = get_sole_length_from_size(size)

    # -------------------------------
    # Read input image
    # -------------------------------
    base_image = await input_image.read()
    images = [("base.png", base_image)]

    if replace_image:
        images.append(("ref.png", await replace_image.read()))

    edit_prompt = build_size_aware_prompt(prompt, size)

    # -------------------------------
    # Generate edited image
    # -------------------------------
    result = client.images.edit(
        model="gpt-image-1",
        image=images,
        prompt=edit_prompt,
        size="1024x1024"
    )

    edited_image = base64.b64decode(result.data[0].b64_json)
    image_id = str(uuid.uuid4())

    edited_path = f"{STATIC_DIR}/{image_id}_edited.png"
    with open(edited_path, "wb") as f:
        f.write(edited_image)

    # -------------------------------
    # Generate orthographic views
    # (IMPORTANT: from EDITED image)
    # -------------------------------
    top_view = generate_single_view(edited_image, "top", sole_length_mm)
    side_view = generate_single_view(edited_image, "side", sole_length_mm)
    front_view = generate_single_view(edited_image, "front", sole_length_mm)

    with open(f"{STATIC_DIR}/{image_id}_top.png", "wb") as f:
        f.write(top_view)

    with open(f"{STATIC_DIR}/{image_id}_side.png", "wb") as f:
        f.write(side_view)

    with open(f"{STATIC_DIR}/{image_id}_front.png", "wb") as f:
        f.write(front_view)

    # -------------------------------
    # BOM
    # -------------------------------
    bom = generate_bom_from_image(edited_image)

    return JSONResponse({
        "status": "success",
        "size": size,
        "sole_length_mm": sole_length_mm,
        "bom": bom,
        "views": {
            "edited": f"/image/static/{image_id}_edited.png",
            "top": f"/image/static/{image_id}_top.png",
            "side": f"/image/static/{image_id}_side.png",
            "front": f"/image/static/{image_id}_front.png"
        }
    })
