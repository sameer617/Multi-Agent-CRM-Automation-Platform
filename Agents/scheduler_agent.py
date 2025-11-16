import os
import re
import ssl
import smtplib
import imaplib
import email
import json
from datetime import datetime, timedelta
from typing import TypedDict, List, Dict, Any
from dateutil import parser as dparser
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# ==========================================================
# 🔧 Load environment
# ==========================================================
load_dotenv()
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASS = os.getenv("SMTP_PASS")

# ==========================================================
# 📦 Scheduler State
# ==========================================================
class SchedulerState(TypedDict):
    responses: List[Dict[str, Any]]
    scheduled_meetings: List[Dict[str, Any]]
    follow_ups_sent: List[Dict[str, Any]]

# ==========================================================
# 🤖 LLM for Sentiment + Intent Understanding
# ==========================================================
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

intent_prompt = PromptTemplate(
    input_variables=["reply_text"],
    template=(
        "You are an AI assistant analyzing an email reply to schedule a meeting.\n"
        "Analyze the tone and extract any explicit availability if present.\n\n"
        "Email reply:\n{reply_text}\n\n"
        "Rules:\n"
        "- If the message shows any willingness to meet or positive interest, set 'sentiment' = 'positive'.\n"
        "- If they refuse, decline, or not interested, set 'sentiment' = 'negative'.\n"
        "- Otherwise, set 'sentiment' = 'neutral'.\n"
        "- If the message mentions a day or date (e.g., 'next Tuesday', 'Nov 18', 'tomorrow 3 PM'), extract it as 'availability'.\n"
        "- If no such time is found, set 'availability' = null.\n\n"
        "Return a valid JSON object strictly in this format:\n"
        "{{\"sentiment\": \"positive|neutral|negative\", \"availability\": \"<text or null>\"}}"
    ),
)

# ==========================================================
# 📅 Utility — Extract meeting datetime from text
# ==========================================================
def extract_meeting_datetime(reply_text: str) -> datetime | None:
    if not reply_text:
        return None
    txt = reply_text.lower().strip()
    today = datetime.now()

    # Common relative cases
    if "tomorrow" in txt:
        match = re.search(r"(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm)?", txt)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2) or 0)
            if match.group(3) and match.group(3).lower() == "pm" and hour < 12:
                hour += 12
            return today.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=1)
        return today + timedelta(days=1)

    if "next week" in txt:
        return today + timedelta(days=7)

    # Use dateutil parser for specific dates
    try:
        parsed = dparser.parse(txt, fuzzy=True, default=today)
        if parsed < today:
            # If parsed datetime already passed, assume next occurrence
            parsed = parsed.replace(year=today.year + 1)
        return parsed
    except Exception:
        return None

# ==========================================================
# 📤 Utility — Send Email via SMTP
# ==========================================================
def send_followup_email(to_email: str, subject: str, body: str) -> None:
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_EMAIL
    msg["To"] = to_email

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(SMTP_EMAIL, SMTP_PASS)
            server.sendmail(SMTP_EMAIL, [to_email], msg.as_string())
        print(f"📨 Follow-up email sent to {to_email}")
    except Exception as e:
        print(f"⚠️ Failed to send follow-up email to {to_email}: {e}")

# ==========================================================
# 📆 Utility — Create Google Calendar Event
# ==========================================================
def create_calendar_event(to_email: str, meeting_time: datetime) -> Dict[str, Any]:
    try:
        creds = Credentials.from_authorized_user_file("token.json", ["https://www.googleapis.com/auth/calendar"])
        service = build("calendar", "v3", credentials=creds)

        start_time = meeting_time.isoformat()
        end_time = (meeting_time + timedelta(hours=1)).isoformat()

        event = {
            "summary": "TechNova Discovery Call",
            "location": "Google Meet",
            "description": "Discovery meeting with prospective client to discuss consulting opportunities.",
            "start": {"dateTime": start_time, "timeZone": "America/New_York"},
            "end": {"dateTime": end_time, "timeZone": "America/New_York"},
            "attendees": [{"email": to_email}],
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 30},
                    {"method": "popup", "minutes": 10},
                ],
            },
        }

        event = service.events().insert(calendarId="primary", body=event, sendUpdates="all").execute()
        print(f"📆 Meeting scheduled with {to_email} at {meeting_time}")
        return {"email": to_email, "event_id": event.get("id"), "meeting_time": str(meeting_time)}

    except Exception as e:
        print(f"⚠️ Error creating calendar event for {to_email}: {e}")
        return {"email": to_email, "error": str(e)}

# ==========================================================
# 🧠 Scheduler Agent Node
# ==========================================================
def scheduler_agent_node(state: SchedulerState) -> SchedulerState:
    responses = state.get("responses", [])
    scheduled_meetings = state.get("scheduled_meetings", [])
    follow_ups_sent = state.get("follow_ups_sent", [])

    for r in responses:
        email_addr = r["email"]
        reply_text = r.get("reply")

        if not reply_text:
            continue

        # --- Step 1: Infer sentiment & availability
        intent_json = llm.invoke(intent_prompt.format(reply_text=reply_text)).content
        try:
            intent_data = json.loads(intent_json)
        except Exception:
            intent_data = {"sentiment": "neutral", "availability": None}

        if not intent_data.get("availability"):
        # Simple regex check for common time phrases
            date_match = re.search(r"(?:\b(?:mon|tue|wed|thu|fri|sat|sun)\b|"
                                r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b)"
                                r".{0,20}?\b\d{1,2}\b.*?(?:am|pm)?", reply_text, re.IGNORECASE)
            if date_match:
                intent_data["availability"] = date_match.group(0)
                intent_data["sentiment"] = "positive"

        sentiment = intent_data.get("sentiment", "neutral")
        availability = intent_data.get("availability")

        print(f"\nAvail_Resp {intent_data}")
        print(f"Availability {availability}")

        # --- Step 2: Handle positive sentiment cases
        if sentiment == "positive":
            meeting_time = None
            if availability:
                meeting_time = extract_meeting_datetime(availability)
            else:
                meeting_time = extract_meeting_datetime(reply_text)

            if meeting_time:
                meeting_info = create_calendar_event(email_addr, meeting_time)
                scheduled_meetings.append(meeting_info)
            else:
                # Ask for time options
                subject = "Scheduling Your Discovery Call"
                body = (
                    f"Hi,\n\nThanks for your interest in connecting with TechNova Consulting! "
                    f"Could you please share your availability this week for a quick 30-min call?\n\n"
                    f"Best,\nTechNova Team"
                )
                send_followup_email(email_addr, subject, body)
                follow_ups_sent.append({"email": email_addr, "status": "follow-up sent"})

        # --- Step 3: Handle negative sentiment
        elif sentiment == "negative":
            print(f"🙅 Skipping scheduling for {email_addr} — user not interested.")

    return {
        "responses": responses,
        "scheduled_meetings": scheduled_meetings,
        "follow_ups_sent": follow_ups_sent,
    }

# ==========================================================
# 🔗 LangGraph Setup
# ==========================================================
graph = StateGraph(SchedulerState)
graph.add_node("SchedulerAgent", scheduler_agent_node)
graph.set_entry_point("SchedulerAgent")
graph.add_edge("SchedulerAgent", END)
scheduler_graph = graph.compile()

# ==========================================================
# 🧪 Standalone Demo
# ==========================================================
if __name__ == "__main__":
    mock_responses = [
        {
            "email": "sameer19@umd.edu",
            "reply": "Yes, I’m available next Tuesday, November 18, 2025 at 10 AM.",
            "status": "replied",
        },
        {
            "email": "sameer.pandey627@gmail.com",
            "reply": "Can we talk sometime next week?",
            "status": "replied",
        },
    ]

    init_state = {
        "responses": mock_responses,
        "scheduled_meetings": [],
        "follow_ups_sent": [],
    }

    output = scheduler_graph.invoke(init_state)
    print("\n📊 Final Scheduler Output:")
    print(json.dumps(output, indent=2))
