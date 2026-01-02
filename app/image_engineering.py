from fastapi import APIRouter, Form, UploadFile, File
from fastapi.responses import JSONResponse
from openai import OpenAI
import base64
import uuid
import json
import re
import os
import requests

# =========================================================
# ROUTER SETUP
# =========================================================
router = APIRouter(prefix="/image", tags=["Image Engineering"])

# =========================================================
# PATH SETUP
# =========================================================
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(ROOT_DIR, "app", "static")

os.makedirs(STATIC_DIR, exist_ok=True)
STATIC_FILES_PATH = STATIC_DIR

print("=" * 60)
print("📂 IMAGE ENGINEERING MODULE")
print("📂 STATIC_DIR:", STATIC_DIR)
print("=" * 60)

# =========================================================
# OPENAI CLIENT
# =========================================================
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# =========================================================
# SIZE → SOLE LENGTH
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
        raise ValueError("Invalid JSON from model")

# =========================================================
# SIZE-AWARE + REPLACE-ONLY PROMPT
# =========================================================
def build_size_aware_prompt(user_prompt: str, size: int) -> str:
    sole_length = get_sole_length_from_size(size)

    return f"""
{user_prompt}

MANUFACTURING CONSTRAINTS:
- Footwear size: UK/India {size}
- Sole length: {sole_length} mm (PRIMARY SCALE REFERENCE)
- Maintain realistic adult footwear proportions

STRICT RULES:
- Modify ONLY the requested decorative object
- Preserve footwear geometry exactly
- Do NOT change shape, size, alignment, or position
- Do NOT re-center or rescale the product
- Integrate replacement naturally with lighting & shadows
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
# MAIN API – IMAGE OBJECT REPLACEMENT
# =========================================================
@router.post("/replace")
async def replace(
    image_url: str = Form(...),
    prompt: str = Form(...),
    size: int = Form(...),
    replace_image: UploadFile | None = File(None)
):
    print("\n" + "=" * 60)
    print("📥 IMAGE REPLACE REQUEST")
    print("Image URL:", image_url)
    print("Prompt:", prompt)
    print("Size:", size)
    print("Replace image provided:", bool(replace_image))
    print("=" * 60)

    # -----------------------------------------------------
    # LOAD BASE IMAGE (LOCAL OR REMOTE)
    # -----------------------------------------------------
    try:
        if image_url.startswith("http://127.0.0.1") or image_url.startswith("http://localhost"):
            filename = image_url.split("/")[-1]
            local_path = os.path.join(STATIC_DIR, filename)

            if not os.path.exists(local_path):
                return JSONResponse(
                    status_code=400,
                    content={"error": f"Local image not found: {filename}"}
                )

            with open(local_path, "rb") as f:
                base_image = f.read()
        else:
            resp = requests.get(image_url, timeout=15)
            if resp.status_code != 200:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Failed to download image"}
                )
            base_image = resp.content

    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"error": f"Image load failed: {str(e)}"}
        )

    # -----------------------------------------------------
    # OPENAI IMAGE EDIT (REPLACE OBJECT)
    # -----------------------------------------------------
    try:
        images = [("base.png", base_image)]

        if replace_image:
            ref_bytes = await replace_image.read()
            images.append(("ref.png", ref_bytes))

        edit_prompt = build_size_aware_prompt(prompt, size)

        result = client.images.edit(
            model="gpt-image-1",
            image=images,
            prompt=edit_prompt,
            size="1024x1024"
        )

        edited_image = base64.b64decode(result.data[0].b64_json)

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Image editing failed: {str(e)}"}
        )

    # -----------------------------------------------------
    # SAVE EDITED IMAGE
    # -----------------------------------------------------
    image_id = str(uuid.uuid4())
    filename = f"{image_id}_edited.png"
    save_path = os.path.join(STATIC_DIR, filename)

    with open(save_path, "wb") as f:
        f.write(edited_image)

    # -----------------------------------------------------
    # GENERATE BOM
    # -----------------------------------------------------
    try:
        bom = generate_bom_from_image(edited_image)
    except Exception:
        bom = {"product_name": "Unknown", "components": []}

    # -----------------------------------------------------
    # RESPONSE
    # -----------------------------------------------------
    return JSONResponse(
        content={
            "status": "success",
            "size": size,
            "sole_length_mm": get_sole_length_from_size(size),
            "bom": bom,
            "views": {
                "edited": f"/image/static/{filename}"
            }
        }
    )

# =========================================================
# HEALTH CHECK
# =========================================================
@router.get("/health")
async def health():
    return {
        "status": "healthy",
        "static_dir": STATIC_DIR,
        "openai_key_configured": bool(os.getenv("OPENAI_API_KEY"))
    }
