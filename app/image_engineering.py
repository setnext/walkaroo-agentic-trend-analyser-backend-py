from fastapi import APIRouter, Form
from fastapi.responses import JSONResponse
from openai import OpenAI
import base64
import uuid
import json
import re
import os
import requests
from fastapi.staticfiles import StaticFiles 

# =========================================================
# ROUTER SETUP
# =========================================================
router = APIRouter(prefix="/image", tags=["Image Engineering"])

# =========================================================
# PATH SETUP
# =========================================================
# Get the root directory (parent of app/)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(ROOT_DIR, "app", "static")

os.makedirs(STATIC_DIR, exist_ok=True)

print("=" * 60)
print("📂 IMAGE ENGINEERING MODULE")
print("📂 ROOT_DIR:", ROOT_DIR)
print("📂 STATIC_DIR:", STATIC_DIR)
print("📂 STATIC DIR EXISTS:", os.path.exists(STATIC_DIR))
print("=" * 60)

# =========================================================
# OPENAI CLIENT
# =========================================================
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
STATIC_FILES_PATH = STATIC_DIR
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
    """Convert shoe size to sole length in millimeters"""
    if size not in SIZE_TO_SOLE_MM:
        raise ValueError("Unsupported size")
    return SIZE_TO_SOLE_MM[size]

# =========================================================
# SAFE JSON EXTRACTION
# =========================================================
def extract_json(text: str) -> dict:
    """Extract and parse JSON from text, handling markdown code blocks"""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError("Invalid JSON from model")

# =========================================================
# SIZE-AWARE PROMPT
# =========================================================
def build_size_aware_prompt(user_prompt: str, size: int) -> str:
    """Build a prompt with manufacturing constraints based on size"""
    sole_length = get_sole_length_from_size(size)
    return f"""
{user_prompt}

MANUFACTURING CONSTRAINTS:
- Footwear size: UK/India {size}
- Sole length: {sole_length} mm (PRIMARY SCALE)
- Maintain realistic adult footwear proportions
- Use millimeters only
"""

# =========================================================
# BOM GENERATION
# =========================================================
def generate_bom_from_image(image_bytes: bytes) -> dict:
    """Generate Bill of Materials from product image using GPT-4 Vision"""
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "You are a footwear BOM expert. Return ONLY valid JSON."
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
# MAIN API ENDPOINT - IMAGE REPLACEMENT
# =========================================================
@router.post("/replace")
async def replace(
    image_url: str = Form(...),
    prompt: str = Form(...),
    size: int = Form(...)
):
    """
    Edit an image based on user prompt with size-aware constraints
    
    Args:
        image_url: URL of the image to edit (can be local or remote)
        prompt: User's modification request
        size: Shoe size (5-10)
    
    Returns:
        JSON with edited image URL and bill of materials
    """
    print("\n" + "=" * 60)
    print("📥 IMAGE REPLACE REQUEST")
    print("=" * 60)
    print("Image URL:", image_url)
    print("Prompt:", prompt)
    print("Size:", size)

    # ---------------------------------
    # Get image (handle both local and remote URLs)
    # ---------------------------------
    try:
        # Check if it's a local file reference
        if image_url.startswith("http://127.0.0.1") or image_url.startswith("http://localhost"):
            # Extract filename from local URL
            filename = image_url.split("/")[-1]
            local_path = os.path.join(STATIC_DIR, filename)
            
            if os.path.exists(local_path):
                print(f"📂 Reading local file: {local_path}")
                with open(local_path, "rb") as f:
                    base_image = f.read()
            else:
                return JSONResponse(
                    status_code=400,
                    content={"error": f"Local file not found: {filename}"}
                )
        else:
            # Download from external URL
            print(f"⬇️ Downloading from: {image_url}")
            resp = requests.get(image_url, timeout=15)
            if resp.status_code != 200:
                return JSONResponse(
                    status_code=400,
                    content={"error": f"Failed to download image: HTTP {resp.status_code}"}
                )
            base_image = resp.content
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"error": f"Failed to get image: {str(e)}"}
        )

    # ---------------------------------
    # OpenAI Image Edit
    # ---------------------------------
    try:
        edit_prompt = build_size_aware_prompt(prompt, size)

        result = client.images.edit(
            model="gpt-image-1",
            image=[("base.png", base_image)],
            prompt=edit_prompt,
            size="1024x1024"
        )

        edited_image = base64.b64decode(result.data[0].b64_json)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Image editing failed: {str(e)}"}
        )

    # ---------------------------------
    # SAVE EDITED IMAGE
    # ---------------------------------
    image_id = str(uuid.uuid4())
    filename = f"{image_id}_edited.png"
    edited_path = os.path.join(STATIC_DIR, filename)
    
    print("\n🔍 SAVE DIAGNOSTICS:")
    print("   STATIC_DIR:", STATIC_DIR)
    print("   Filename:", filename)
    print("   Full path:", edited_path)
    
    try:
        with open(edited_path, "wb") as f:
            f.write(edited_image)

        print("✅ Saved edited image")
        print("✅ File exists:", os.path.exists(edited_path))
        print("✅ File size:", os.path.getsize(edited_path), "bytes")
        
        # List files in static dir to verify
        files_in_static = os.listdir(STATIC_DIR)
        print("✅ Total files in STATIC_DIR:", len(files_in_static))
    except Exception as e:
        print(f"❌ SAVE ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to save image: {str(e)}"}
        )

    # ---------------------------------
    # Generate BOM
    # ---------------------------------
    try:
        print("🔄 Generating BOM...")
        bom = generate_bom_from_image(edited_image)
        print("✅ BOM generated successfully")
    except Exception as e:
        print(f"⚠️ BOM generation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        bom = {
            "product_name": "Unknown Product",
            "components": []
        }

    # ---------------------------------
    # Build Response
    # ---------------------------------
    response_data = {
        "status": "success",
        "size": size,
        "sole_length_mm": get_sole_length_from_size(size),
        "bom": bom,
        "views": {
            "edited": f"/image/static/{filename}"
        }
    }
    
    print("\n📤 RESPONSE:")
    print("   URL:", f"http://127.0.0.1:8000/image/static/{filename}")
    print("=" * 60 + "\n")

    return JSONResponse(response_data)

# =========================================================
# HEALTH CHECK
# =========================================================
@router.get("/health")
async def health_check():
    """Check if image engineering service is working"""
    return {
        "status": "healthy",
        "service": "Image Engineering",
        "static_dir": STATIC_DIR,
        "static_dir_exists": os.path.exists(STATIC_DIR),
        "openai_configured": bool(os.getenv("OPENAI_API_KEY"))
    }
