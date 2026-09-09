from dotenv import load_dotenv

load_dotenv()
import base64
import os
from bson import ObjectId
from google import genai
from google.genai import types
from pdf2image import convert_from_path

from ..db.collections.files import files_collection

# Gemini client automatically picks up GEMINI_API_KEY from environment
client = genai.Client()


def encode_image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def analyze_image_with_gemini(base64_string: str, mime_type: str = "image/jpeg"):
    # Decode base64 and send bytes inline to Gemini
    image_bytes = base64.b64decode(base64_string)
    
    config = types.GenerateContentConfig(
        safety_settings=[
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            ),
        ]
    )
    
    response = client.models.generate_content(
        model = "gemini-3.1-flash-lite",
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            "Extract all text, tables, and list all information from this document page.",
        ],
        config=config
    )
    return response.text


async def process_file(id: str, file_path: str):
    await files_collection.update_one(
        {"_id": ObjectId(id)},
        {"$set": {"status": "converting to images"}},
    )

    # Step 1: Convert PDF to images
    pages = convert_from_path(file_path)
    page_analyses = []

    # Step 2: Save and process each page
    for i, page in enumerate(pages):
        image_save_path = f"/mnt/uploads/images/{id}/image-{i}.jpg"
        os.makedirs(os.path.dirname(image_save_path), exist_ok=True)
        page.save(image_save_path, "JPEG")

        # Encode to base64 & call Gemini
        base64_img = encode_image_to_base64(image_save_path)
        extracted_text = analyze_image_with_gemini(base64_img, mime_type="image/jpeg")

        page_analyses.append(
            {
                "page": i + 1,
                "image_path": image_save_path,
                "content": extracted_text,
            }
        )

    # Step 3: Save analysis results and update status
    await files_collection.update_one(
        {"_id": ObjectId(id)},
        {
            "$set": {
                "status": "completed",
                "pages": page_analyses,
            }
        },
    )