import os
import asyncio
import ssl
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from typing import TypedDict, List, Dict, Any
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
import json
import re
# ==========================================================
# 🔧 1️⃣  Load environment variables (.env)
# ==========================================================
load_dotenv()
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASS = os.getenv("SMTP_PASS")

# ==========================================================
# 🧩 2️⃣  Define State Schema
# ==========================================================
class InteractionState(TypedDict):
    shortlisted: List[Dict[str, Any]]
    emails_sent: List[Dict[str, Any]]
    responses: List[Dict[str, Any]]

# ==========================================================
# 🤖 3️⃣  Initialize LLM for Email Drafting
# ==========================================================
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.4, api_key=os.getenv("OPENAI_API_KEY"))

email_prompt = PromptTemplate(
    input_variables=["company_name", "industry", "company_description"],
    template=(
        "You are an AI outreach assistant at TechNova Consulting.\n"
        "Compose a short, professional outreach email to the CEO of {company_name} "
        "(operating in {industry}). The email should:\n"
        "- Highlight TechNova’s relevant expertise.\n"
        "- Sound conversational and human.\n"
        "- End with a call-to-action for a discovery call.\n\n"
        "Company description:\n{company_description}\n\n"
        "Return JSON with 'subject' and 'body'."
    ),
)

# ==========================================================
# 📤 4️⃣  Send Email via SMTP (Gmail)
# ==========================================================
def send_email_smtp(to_email: str, subject: str, body: str) -> Dict[str, Any]:
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_EMAIL
    msg["To"] = to_email

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(SMTP_EMAIL, SMTP_PASS)
            server.sendmail(SMTP_EMAIL, [to_email], msg.as_string())
        print(f"✅ Sent email to {to_email}")
        return {"email": to_email, "status": "sent", "subject": subject}
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {e}")
        return {"email": to_email, "status": "failed", "error": str(e)}

# ==========================================================
# 📥 5️⃣  Check for Replies via IMAP (Gmail Inbox)
# ==========================================================
from datetime import datetime, timedelta

def read_latest_reply(from_email: str) -> str | None:
    """Fetch latest real reply message from the given email."""
    try:
        import imaplib, email, re
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(SMTP_EMAIL, SMTP_PASS)
        # Search across All Mail to avoid inbox filter issues
        mail.select('"[Gmail]/All Mail"')

        # Search for messages FROM that contact in last 5 days
        result, data = mail.search(None, f'(FROM "{from_email}" SINCE "05-Nov-2025")')
        if result != "OK" or not data[0]:
            return None

        ids = data[0].split()
        latest_id = ids[-1]
        result, msg_data = mail.fetch(latest_id, "(RFC822)")
        raw = email.message_from_bytes(msg_data[0][1])

        # Extract plain text content
        body = ""
        if raw.is_multipart():
            for part in raw.walk():
                if part.get_content_type() == "text/plain":
                    body += part.get_payload(decode=True).decode(errors="ignore")
        else:
            body = raw.get_payload(decode=True).decode(errors="ignore")

        # 🧹 Clean and detect valid human reply
        body = re.sub(r"(On .+?wrote:).*", "", body, flags=re.DOTALL)  # cut quoted message
        body = body.strip().replace("\n", " ")

        # Filter out system messages or automated replies
        ignore_patterns = ["Google Drive", "requests access", "out of office", "autoreply"]
        if any(p.lower() in body.lower() for p in ignore_patterns):
            print(f"⚠️ Ignored system message from {from_email}")
            return None

        # Limit to a short readable snippet
        snippet = body[:250].strip()
        if snippet:
            print(f"✅ Detected reply from {from_email}: {snippet[:100]}...")
            return snippet
        return None

    except Exception as e:
        print(f"⚠️ Error checking replies: {e}")
        return None
    finally:
        try:
            mail.logout()
        except:
            pass




# ==========================================================
# ⏳ 6️⃣  Asynchronous Polling for Replies
# ==========================================================
async def wait_for_reply(from_email: str, timeout_minutes: int = 3, interval_sec: int = 10):
    """
    Periodically checks inbox for reply within timeout_minutes.
    """
    total_wait = 0
    while total_wait < timeout_minutes * 60:
        reply = read_latest_reply(from_email)
        if reply:
            if reply.strip().lower() in ["none", "null", "no reply"]:
                reply = None
            return {"email": from_email, "reply": reply, "status": "replied"}
        await asyncio.sleep(interval_sec)
        total_wait += interval_sec
    print(f"⌛ No reply from {from_email} within timeout window.")
    return {"email": from_email, "reply": None, "status": "no_reply"}

# ==========================================================
# 🧠 7️⃣  Interaction Agent Node
# ==========================================================
async def interaction_agent_node(state: InteractionState) -> InteractionState:
    shortlisted = state["shortlisted"]
    emails_sent, responses = [], []

    async def process_lead(lead):
        """Send email and asynchronously wait for reply."""
        company_name = lead["company_name"]
        industry = lead["industry"]
        description = lead["company_description"]
        contact = lead["contact_email"]

        try:
            content = llm.invoke(
                email_prompt.format(
                    company_name=company_name,
                    industry=industry,
                    company_description=description,
                )
            ).content
        except Exception as e:
            print(f"⚠️ LLM generation failed for {company_name}: {e}")
            return {"email": contact, "reply": None, "status": "failed"}

        # Clean up markdown code fences (```json ... ```)
        cleaned = re.sub(r"^```(json)?|```$", "", content.strip(), flags=re.MULTILINE).strip()

        try:
            email_data = json.loads(cleaned)
        except json.JSONDecodeError:
            print(f"⚠️ Could not parse JSON output for {company_name}, using raw text instead.")
            email_data = {
                "subject": f"Exploring Collaboration with {company_name}",
                "body": cleaned,
            }

        # Send email via SMTP
        sent_info = send_email_smtp(contact, email_data["subject"], email_data["body"])
        emails_sent.append(sent_info)

        # Start reply checking (non-blocking)
        reply_info = await wait_for_reply(contact)
        return reply_info

    # ✅ Send all emails + wait concurrently
    print("🚀 Sending outreach emails asynchronously...")
    tasks = [asyncio.create_task(process_lead(lead)) for lead in shortlisted]
    results = await asyncio.gather(*tasks)

    # Collect results
    for res in results:
        if res:
            responses.append(res)

    print("✅ Interaction completed — all outreach tasks processed.")
    return {"shortlisted": shortlisted, "emails_sent": emails_sent, "responses": responses}


# ==========================================================
# 🧩 8️⃣  LangGraph Setup
# ==========================================================
graph = StateGraph(InteractionState)
graph.add_node("InteractionAgent", interaction_agent_node)
graph.set_entry_point("InteractionAgent")
graph.add_edge("InteractionAgent", END)
interaction_graph = graph.compile()

# ==========================================================
# 🧪 9️⃣  Run Standalone Demo
# ==========================================================
if __name__ == "__main__":
    async def demo_run():
        shortlisted = [
            {
                "company_name": "CloudXpert Inc.",
                "industry": "SaaS & Cloud Infrastructure",
                "company_description": "CloudXpert provides scalable SaaS solutions...",
                "contact_email": "sameer.pandey627@gmail.com"
            },
            {
                "company_name": "SecureNet Systems",
                "industry": "Cybersecurity",
                "company_description": "SecureNet offers cloud threat intelligence...",
                "contact_email": "sameer19@umd.edu"
            }
        ]

        state = {"shortlisted": shortlisted, "emails_sent": [], "responses": []}
        result = await interaction_graph.ainvoke(state)
        print("\n📊 Final Interaction Summary:")
        for r in result["responses"]:
            print(f"- {r['email']} → {r['status']}")
            if r["reply"]:
                print(f"  ↳ {r['reply'][:100]}...")

    asyncio.run(demo_run())
