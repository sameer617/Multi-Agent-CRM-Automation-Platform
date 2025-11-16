import streamlit as st
import sys
import os
import json
import time
import threading
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

# ------------------------------------------------------------
# ✅ PATH FIX — Ensure Agents folder is importable
# ------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AGENTS_DIR = os.path.join(BASE_DIR, "Agents")
if AGENTS_DIR not in sys.path:
    sys.path.append(AGENTS_DIR)

# ------------------------------------------------------------
# ✅ Import agents
# ------------------------------------------------------------
from supervisor_agent import load_companies
from recruitment_agent import recruitment_graph
from interaction_agent import send_email_smtp, read_latest_reply
from scheduler_agent import scheduler_graph
from analytics_agent import analytics_graph

# ------------------------------------------------------------
# 🌈 Page Config + Custom CSS Styling
# ------------------------------------------------------------
st.set_page_config(
    page_title="TechNova CRM Dashboard",
    page_icon="🤖",
    layout="wide",
)

st.markdown(
    """
    <style>
        .main {
            background: linear-gradient(180deg, #f9fbff 0%, #f0f4ff 100%);
            padding: 2rem 4rem;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 30px;
            justify-content: center;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 10px 30px;
            border-radius: 10px;
            background-color: #e9efff;
            color: #003366;
            font-weight: 600;
        }
        .stTabs [aria-selected="true"] {
            background-color: #4f83ff !important;
            color: white !important;
        }
        .title-container {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 15px;
        }
        .sidebar .sidebar-content {
            background-color: #eef3ff !important;
        }
        .stButton>button {
            border-radius: 10px;
            background-color: #0052cc !important;
            color: white !important;
            font-weight: 600 !important;
            border: none;
            padding: 8px 18px;
        }
        .stButton>button:hover {
            background-color: #003d99 !important;
        }
        .small-note {
            font-size: 13px;
            color: gray;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# ------------------------------------------------------------
# 🧠 Sidebar Navigation
# ------------------------------------------------------------
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/4240/4240624.png", width=100)
st.sidebar.title("TechNova CRM")
st.sidebar.markdown("---")

tabs = st.sidebar.radio(
    "Navigation",
    ["🏠 Home Dashboard", "🧩 Agents Workflow", "📈 Activity Log", "⚙️ Settings"]
)
st.sidebar.markdown("---")
st.sidebar.caption("© 2025 TechNova Consulting | AI-Powered CRM")

# ------------------------------------------------------------
# 🪵 Logging Helpers
# ------------------------------------------------------------
if "state" not in st.session_state:
    st.session_state.state = {
        "companies": [],
        "shortlisted": [],
        "emails_draft": [],
        "emails_sent": [],
        "responses": [],
        "scheduled_meetings": [],
        "analyses": []
    }

if "logs" not in st.session_state:
    st.session_state.logs = []

if "auto_checking" not in st.session_state:
    st.session_state.auto_checking = False

def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.logs.append(f"[{timestamp}] {msg}")

def log_and_display(msg, icon="🟢"):
    log(f"{icon} {msg}")
    st.write(f"{icon} {msg}")

# ============================================================
# 🏠 HOME DASHBOARD TAB
# ============================================================
if tabs == "🏠 Home Dashboard":
    st.markdown(
        """
        <div class="title-container">
            <img src="https://cdn-icons-png.flaticon.com/512/4712/4712109.png" width="65">
            <h1>🤖 TechNova Multi-Agent CRM System</h1>
        </div>
        <h5 style='text-align:center;color:#4f83ff;'>
        Event-driven LangGraph AI Agents for Customer Discovery & Relationship Management
        </h5>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.image("https://cdn-icons-png.flaticon.com/512/4149/4149677.png", width=140)
        st.markdown("### 🔍 Discover Leads")
        st.caption("Recruitment Agent identifies the best-fit customers from data.")

    with col2:
        st.image("https://cdn-icons-png.flaticon.com/512/4149/4149725.png", width=140)
        st.markdown("### 💌 Automated Outreach")
        st.caption("Interaction Agent drafts and sends personalized outreach emails.")

    with col3:
        st.image("https://cdn-icons-png.flaticon.com/512/4149/4149738.png", width=140)
        st.markdown("### 📅 Smart Scheduling")
        st.caption("Scheduler Agent books meetings via Google Calendar automatically.")

    st.markdown("---")
    st.info("Navigate to **Agents Workflow** tab to start the full demo ➡️")

# ============================================================
# 🧩 AGENTS WORKFLOW TAB
# ============================================================
elif tabs == "🧩 Agents Workflow":

    st.markdown("## 🧩 Agents Workflow Simulation")
    st.caption("End-to-end AI workflow from lead discovery to analytics")

    # Fake tabs for realism
    section = st.tabs(["🏠 Dashboard", "📋 Leads", "💬 Emails", "📅 Meetings", "📊 Insights"])

    # 1️⃣ Recruitment Agent
    with section[1]:
        st.subheader("1️⃣ Recruitment Agent — Lead Discovery")
        if st.button("Run Recruitment Agent 🚀"):
            log_and_display("Recruitment Agent started...", "🧠")
            companies = load_companies()
            recruit_state = {"companies": companies, "shortlisted": []}
            output = recruitment_graph.invoke(recruit_state)
            st.session_state.state["companies"] = companies
            st.session_state.state["shortlisted"] = output["shortlisted"]
            log_and_display(f"{len(output['shortlisted'])} leads shortlisted successfully.", "✅")

            # Increase table visibility
            st.markdown("### 📊 Shortlisted Leads")
            st.dataframe(output["shortlisted"], use_container_width=True, height=600)

    # 2️⃣ Interaction Agent
    with section[2]:
        st.subheader("2️⃣ Interaction Agent — Outreach & Replies")

        if st.session_state.state["shortlisted"]:
            shortlisted = st.session_state.state["shortlisted"]
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.4)

            email_prompt = PromptTemplate(
                input_variables=["company_name", "industry", "company_description"],
                template=(
                    "You are an outreach assistant at TechNova Consulting.\n"
                    "Compose a professional outreach email to the CEO of {company_name} "
                    "(in {industry}) highlighting TechNova’s expertise in AI and MLOps. "
                    "End with a polite discovery call invitation. Return JSON with 'subject' and 'body'.\n\n"
                    "Company description:\n{company_description}"
                ),
            )

            if st.button("Generate Email Drafts ✉️"):
                drafts = []
                log_and_display("Generating outreach drafts...", "🧠")
                for lead in shortlisted:
                    response = llm.invoke(
                        email_prompt.format(
                            company_name=lead["company_name"],
                            industry=lead["industry"],
                            company_description=lead["company_description"]
                        )
                    )
                    try:
                        data = json.loads(response.content.strip("```json").strip("```"))
                    except:
                        data = {"subject": "Let's Collaborate", "body": response.content}
                    lead["email_subject"] = data["subject"]
                    lead["email_body"] = data["body"]
                    drafts.append(lead)
                st.session_state.state["emails_draft"] = drafts
                log_and_display("Draft generation completed.", "✅")

            if st.session_state.state["emails_draft"]:
                st.markdown("### Review & Approve Emails")
                approved = []
                for lead in st.session_state.state["emails_draft"]:
                    with st.expander(f"📩 {lead['company_name']} — {lead['contact_email']}"):
                        st.write(f"**Subject:** {lead['email_subject']}")
                        st.markdown(lead["email_body"])
                        approve = st.checkbox(f"Approve sending email to {lead['company_name']}")
                        if approve:
                            approved.append(lead)
                if st.button("Send Approved Emails 🚀"):
                    sent = []
                    for lead in approved:
                        send_email_smtp(
                            lead["contact_email"], lead["email_subject"], lead["email_body"]
                        )
                        log_and_display(f"Email sent to {lead['contact_email']}", "📨")
                        sent.append(lead)
                    st.session_state.state["emails_sent"] = sent
                    log_and_display("All approved emails sent successfully.", "✅")

            # 📨 Check Replies Section
            st.markdown("---")
            st.subheader("📬 Waiting for Customer Replies")

            if st.button("Check for Replies 🔄"):
                replies = []
                for sent in st.session_state.state.get("emails_sent", []):
                    email_id = sent["contact_email"]
                    snippet = read_latest_reply(email_id)
                    if snippet:
                        replies.append({"email": email_id, "reply": snippet})
                        log_and_display(f"Reply from {email_id}: {snippet[:120]}", "💬")

                if replies:
                    st.session_state.state["responses"] = replies
                    log_and_display("Replies detected! Scheduler Agent unlocked.", "✅")
                    st.success("✅ Replies detected! Scheduler Agent is now active.")
                else:
                    st.info("No new replies detected yet. Try again after a few seconds.")

            # 🧾 Always show stored replies
            if st.session_state.state.get("responses"):
                st.markdown("### 💬 Customer Replies Received")
                for r in st.session_state.state["responses"]:
                    with st.expander(f"📧 {r['email']}"):
                        st.markdown(
                            f"""
                            <div style='background-color:#f7faff;padding:10px;border-radius:8px;border-left:5px solid #4f83ff;'>
                                <b>From:</b> {r['email']}<br>
                                <b>Message:</b><br>
                                <pre style='white-space: pre-wrap; font-family: "Inter", sans-serif;'>{r['reply']}</pre>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

            # Optional: Auto-check every 10s
            def auto_check_replies():
                while st.session_state.auto_checking:
                    replies = []
                    for sent in st.session_state.state.get("emails_sent", []):
                        email_id = sent["contact_email"]
                        snippet = read_latest_reply(email_id)
                        if snippet:
                            replies.append({"email": email_id, "reply": snippet})
                    if replies:
                        st.session_state.state["responses"] = replies
                        st.session_state.auto_checking = False
                    time.sleep(10)

            if st.button("Start Auto-Check for Replies ⏱️"):
                st.session_state.auto_checking = True
                threading.Thread(target=auto_check_replies, daemon=True).start()
                st.info("🔁 Auto-checking inbox every 10 seconds...")

        else:
            st.info("Please run the Recruitment Agent first.")

    # 3️⃣ Scheduler Agent
    with section[3]:
        st.subheader("3️⃣ Scheduler Agent — Meeting Scheduling")
        if st.session_state.state["responses"]:
            if st.button("Schedule Meetings 📅"):
                responses = st.session_state.state["responses"]
                state = {"responses": responses, "scheduled_meetings": [], "follow_ups_sent": []}
                log_and_display("Scheduler Agent initiating meeting creation...", "📅")
                result = scheduler_graph.invoke(state)
                st.session_state.state["scheduled_meetings"] = result.get("scheduled_meetings", [])
                log_and_display("Meetings scheduled successfully.", "✅")
                st.json(result.get("scheduled_meetings", []))
        else:
            st.warning("📭 Waiting for replies before enabling Scheduler Agent.")

    # 4️⃣ Analytics Agent
    with section[4]:
        st.subheader("4️⃣ Analytics Agent — Post-Call Insights")
        if st.session_state.state["scheduled_meetings"]:
            if st.button("Run Analytics 📊"):
                analytics_state = {"transcripts": [], "analyses": []}
                if os.path.exists("call_transcripts.json"):
                    with open("call_transcripts.json", "r", encoding="utf-8") as f:
                        analytics_state["transcripts"] = json.load(f)
                result = analytics_graph.invoke(analytics_state)
                st.session_state.state["analyses"] = result.get("analyses", [])
                log_and_display("Analytics Agent completed successfully.", "✅")
                st.json(result.get("analyses", []))
        else:
            st.info("Meetings must be scheduled before analytics can run.")

# ============================================================
# 📈 ACTIVITY LOG TAB
# ============================================================
elif tabs == "📈 Activity Log":
    st.markdown("## 🪵 System Activity Log")
    st.text_area("Activity Timeline", "\n".join(st.session_state.logs), height=400)
    st.info("Live logs from all agents appear here in real time.")

# ============================================================
# ⚙️ SETTINGS TAB
# ============================================================
elif tabs == "⚙️ Settings":
    st.markdown("## ⚙️ System Settings")
    st.text_input("Connected Email Account", "technova.crm@gmail.com")
    st.text_input("Google Calendar Integration", "✅ Active")
    st.text_input("OpenAI Model", "gpt-4o-mini")
    st.text_area("SMTP Configuration", "smtp.gmail.com:587\nusername: technova.crm@gmail.com")
    st.success("All configurations loaded successfully.")
