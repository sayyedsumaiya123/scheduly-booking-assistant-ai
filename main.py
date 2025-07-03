from typing import Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import pytz
import json
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build
import google.generativeai as genai

# ---- Gemini Setup ----
genai.configure(api_key="AIzaSyBUXh4bSk9d3pDVvavSSAzK6cuun4RoWTk")  # Replace with your Gemini API key
model = genai.GenerativeModel("models/gemini-1.5-pro")

# ---- Google Calendar Setup ----
SERVICE_ACCOUNT_FILE = 'chatbot-464610-8825fc3291ca.json'
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )   
    return build("calendar", "v3", credentials=credentials)

def is_time_available(calendar_id: str, start_time: str, end_time: str) -> bool:
    service = get_calendar_service()
    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=start_time,
        timeMax=end_time,
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    return not events_result.get("items", [])

def create_event(calendar_id: str, title: str, summary: str, start_time: str, end_time: str) -> str:
    service = get_calendar_service()
    event = {
        "summary": title,
        "description": summary,
        "start": {"dateTime": start_time, "timeZone": "Asia/Kolkata"},
        "end": {"dateTime": end_time, "timeZone": "Asia/Kolkata"},
    }
    created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
    return created_event.get('htmlLink', '')

def extract_json_from_response(text: str) -> dict:
    try:
        return json.loads(text.strip())
    except:
        try:
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            return {}
        except:
            return {}

def parse_time_with_context(time_str: str, input_message: str) -> str:
    try:
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        time_patterns = [
            (r'(\d{1,2})\s*(?:pm|PM)', lambda m: f"{now.strftime('%Y-%m-%d')}T{int(m.group(1)) + 12 if int(m.group(1)) != 12 else 12:02d}:00:00+05:30"),
            (r'(\d{1,2})\s*(?:am|AM)', lambda m: f"{now.strftime('%Y-%m-%d')}T{int(m.group(1)) if int(m.group(1)) != 12 else 0:02d}:00:00+05:30"),
            (r'(\d{1,2}):(\d{2})\s*(?:pm|PM)', lambda m: f"{now.strftime('%Y-%m-%d')}T{int(m.group(1)) + 12 if int(m.group(1)) != 12 else 12:02d}:{int(m.group(2)):02d}:00+05:30"),
            (r'(\d{1,2}):(\d{2})\s*(?:am|AM)', lambda m: f"{now.strftime('%Y-%m-%d')}T{int(m.group(1)) if int(m.group(1)) != 12 else 0:02d}:{int(m.group(2)):02d}:00+05:30"),
        ]
        for pattern, formatter in time_patterns:
            match = re.search(pattern, input_message.lower())
            if match:
                return formatter(match)
        return "unknown"
    except Exception as e:
        print(f"Time parsing error: {e}")
        return "unknown"

def format_am_pm(iso_string: str) -> str:
    dt = datetime.fromisoformat(iso_string.replace('+05:30', ''))
    return dt.strftime("%I:%M %p on %d %b %Y")

def get_suggested_slots(calendar_id: str) -> str:
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    base = now.replace(hour=9, minute=0, second=0, microsecond=0)
    suggestions = []

    for i in range(8):  # Checking from 9 AM to 11 PM
        slot_start_dt = base + timedelta(hours=i * 2)
        slot_end_dt = slot_start_dt + timedelta(hours=1)

        # Skip past times
        if slot_start_dt <= now:
            continue

        # Format to RFC3339
        slot_start = slot_start_dt.isoformat()
        slot_end = slot_end_dt.isoformat()

        if is_time_available(calendar_id, slot_start, slot_end):
            suggestions.append(f"{slot_start_dt.strftime('%I:%M %p')} - {slot_end_dt.strftime('%I:%M %p')}")

    if suggestions:
        return ", ".join(suggestions)
    else:
        return "No available slots found today."


# ---- FastAPI Setup ----
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.api_route("/health", methods=["GET", "POST"])
async def health_check():
    return {"status": "ok"}

@app.api_route("/setresponse", methods=["GET", "POST"])
async def setresponse(userinput: Dict[str, str]):
    input_message = userinput.get("message", "")
    calendar_id = userinput.get("email", "")
    print("Input received:", input_message)
    print("Calendar ID:", calendar_id)

    current_date = datetime.now().strftime("%Y-%m-%d")

    prompt = f'''You are a smart calendar assistant.

    From the user's input message:
    "{input_message}"

    Respond with ONLY a **valid JSON object**, in one of the following formats:

    {{
        "title": "Meeting title here",
        "summary": "Brief summary here",
        "start": "YYYY-MM-DDTHH:MM:SS+05:30",
        "end": "YYYY-MM-DDTHH:MM:SS+05:30"
    }}

    {{
        "Suggested time slots": "10:00-11:00, 12:30-13:30, 15:00-16:00"
    }}

    Rules:
    - If no date is mentioned, use today’s date: "{current_date}".
    - Use 24-hour format with `+05:30` timezone.
    - If only a start time is mentioned, set end time to 1 hour later.
    - If no time is mentioned, set both start and end to "unknown".
    - Return **ONLY JSON**, no explanations.
    '''

    try:
        response = model.generate_content(prompt)
        result_content = response.text.strip()
        print(f"Gemini raw response: {result_content}")
        extracted = extract_json_from_response(result_content)

        if not extracted:
            start_time = parse_time_with_context("", input_message)
            if start_time != "unknown":
                try:
                    start_dt = datetime.fromisoformat(start_time.replace('+05:30', ''))
                    end_dt = start_dt + timedelta(hours=1)
                    extracted = {
                        "title": "Meeting",
                        "summary": "Meeting scheduled via Scheduly",
                        "start": start_time,
                        "end": end_dt.strftime('%Y-%m-%dT%H:%M:%S+05:30')
                    }
                except:
                    pass

        if not extracted:
            return {
                "status": "suggest",
                "suggestions": get_suggested_slots(calendar_id)

            }

    except Exception as e:
        print(f"Gemini API error: {e}")
        return {
            "status": "error",
            "error": f"AI processing failed: {str(e)}"
        }

    title = extracted.get("title", "Meeting")
    summary = extracted.get("summary", "Meeting scheduled via Scheduly")
    start = extracted.get("start", "unknown")
    end = extracted.get("end", "unknown")

    if start == "unknown":
        return {
            "status": "suggest",
            "suggestions": get_suggested_slots(calendar_id)
        }

    if end == "unknown":
        try:
            start_dt = datetime.fromisoformat(start.replace('+05:30', ''))
            end_dt = start_dt + timedelta(hours=1)
            end = end_dt.strftime('%Y-%m-%dT%H:%M:%S+05:30')
        except Exception as e:
            return {
                "status": "error",
                "error": "Invalid time format detected"
            }

    try:
        ist = pytz.timezone('Asia/Kolkata')
        start_dt = ist.localize(datetime.fromisoformat(start.replace('+05:30', '')))
        end_dt = ist.localize(datetime.fromisoformat(end.replace('+05:30', '')))
    except:
        return {
            "status": "error",
            "error": "Invalid time format"
        }

    now = datetime.now(pytz.timezone('Asia/Kolkata'))
    if start_dt < now:
        return {
            "status": "error",
            "ERROR": "Cannot book. Time slot has already passed.",
            "suggestions": get_suggested_slots(calendar_id)
        }

    try:
        if not is_time_available(calendar_id, start, end):
            return {
                "status": "error",
                "ERROR": "Cannot book. Time slot is already full.",
                "suggestions":get_suggested_slots(calendar_id)
            }
    except Exception as e:
        return {
            "status": "error",
            "error": "Could not check calendar availability"
        }

    try:
        link = create_event(calendar_id, title, summary, start, end)
        return {
            "status": "confirmed",
            "title": title,
            "summary": summary,
            "start": format_am_pm(start),
            "end": format_am_pm(end),
            "link": link
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to create calendar event: {str(e)}"
        }
