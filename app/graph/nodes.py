from dotenv import load_dotenv
load_dotenv()
import json
from bson import ObjectId
from google import genai
from google.genai import types
from app.db.collections.files import files_collection
from .state import AnalysisState

client = genai.Client()


async def fetch_resume_node(state: AnalysisState):
    """Fetches the already-extracted resume text from MongoDB using the file_id."""
    file_id = state.get("file_id")
    try:
        db_file = await files_collection.find_one({"_id": ObjectId(file_id)})
        if not db_file:
            return {"error": f"No file found with id {file_id}"}

        pages = db_file.get("pages", [])
        if not pages:
            return {
                "error": "resume has not been extracted yet, make sure to run the resume extraction step first."
            }

        # Combine text from all pages into a single string
        full_resume_text = "\n\n".join(page.get("content", "") for page in pages)
        return {"resume_text": full_resume_text}
    except Exception as e:
        return {"error": f"error in fetching resume: {str(e)}"}


def rewrite_jd_node(state: AnalysisState):
    """Rewrites and structures the raw job description."""
    if state.get("error"):
        return {}

    raw_jd = state.get("job_description", "")
    prompt = f"""
    You are an expert technical recruiter. Analyze and rewrite the following Job Description.
    Extract:
    1. Core Role Summary
    2. Must-Have Technical Skills & Experience
    3. Good-to-Have / Nice-to-Have Skills
    4. Key Deliverables & Responsibilities
    Raw Job Description:
    \"\"\"{raw_jd}\"\"\"
    """

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt,
    )
    return {"rewritten_jd": response.text}


def generate_report_node(state: AnalysisState):
    """Analyzes gaps and produces specific resume improvements and recommendations."""
    if state.get("error"):
        return {}

    resume_text = state.get("resume_text", "")
    rewritten_jd = state.get("rewritten_jd", "")
    prompt = f"""
    You are a senior technical hiring manager and resume coach.
    Compare the candidate's resume with the job description.
    Job Description (Structured):
    \"\"\"{rewritten_jd}\"\"\"
    Candidate's Extracted Resume:
    \"\"\"{resume_text}\"\"\"
    Provide an actionable evaluation report to help the candidate edit their resume and prepare for the interview.
    Format your output strictly as a JSON object with this schema:
    {{
        "match_percentage": <integer between 0 and 100>,
        "summary": "<2-3 sentence overview of candidate suitability>",
        "strengths": [
            "<strength 1 matching JD>",
            "<strength 2 matching JD>"
        ],
        "weaknesses": [
            "<missing skill or qualification required by JD>",
            "<gap in candidate experience>"
        ],
        "resume_improvements": [
            "<concrete change candidate should make to resume wording, projects, or keywords>",
            "<additional section or metric they should emphasize>"
        ],
        "interview_preparation_tips": [
            "<topic or technical question they must prepare for this specific role>"
        ]
    }}
    Respond ONLY with valid JSON.
    """

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    try:
        report_data = json.loads(response.text)
    except Exception:
        report_data = {"raw_report": response.text}

    return {"report": report_data}