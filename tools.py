# tools.py
from langchain_core.tools import tool
from datetime import datetime

@tool
def send_email_tool(to: str, subject: str, body: str) -> str:
    return f"Email sent to {to} with subject '{subject}'."

@tool
def schedule_meeting_tool(prospect_email: str, prospect_name: str, datetime_iso: str) -> str:
    return f"Meeting with {prospect_name} ({prospect_email}) scheduled at {datetime_iso}."

@tool
def update_crm_stage_tool(prospect_id: int, new_stage: str) -> str:
    return f"Prospect {prospect_id} moved to {new_stage}."

TOOLS = [send_email_tool, schedule_meeting_tool, update_crm_stage_tool]
