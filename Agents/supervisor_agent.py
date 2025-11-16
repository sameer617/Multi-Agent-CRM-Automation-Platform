import os
import json
import asyncio
from typing import TypedDict, Any, Dict, List

from langgraph.graph import StateGraph, END

# Import all agents
from recruitment_agent import recruitment_graph
from interaction_agent import interaction_graph
from scheduler_agent import scheduler_graph
from analytics_agent import analytics_graph

# ==========================================================
# 🧩 State Schema
# ==========================================================
class SupervisorState(TypedDict):
    companies: List[Dict[str, Any]]
    shortlisted: List[Dict[str, Any]]
    emails_sent: List[Dict[str, Any]]
    responses: List[Dict[str, Any]]
    scheduled_meetings: List[Dict[str, Any]]
    transcripts: List[Dict[str, Any]]
    analyses: List[Dict[str, Any]]

# ==========================================================
# 🧠 Utility — Load Synthetic Dataset
# ==========================================================
def load_companies(file_path: str = "synthetic_clients.json") -> List[Dict[str, Any]]:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"❌ Missing {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

# ==========================================================
# ⚙️ Async Helper for Interaction Agent
# ==========================================================
async def run_interaction_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Run Interaction Agent asynchronously."""
    return await interaction_graph.ainvoke(state)

# ==========================================================
# 🧠 Helper — Check if a reply is actually valid
# ==========================================================
def has_valid_reply(r: Dict[str, Any]) -> bool:
    val = r.get("reply")
    if not val or not isinstance(val, str):
        return False
    txt = val.strip().lower()
    if any(bad in txt for bad in ["drive.google.com", "no-reply", "automated message", "requests access"]):
        return False
    if txt in ["none", "null", "", "no reply"]:
        return False
    return True


# ==========================================================
# 🧠 Supervisor Logic — Orchestrates the Whole Flow
# ==========================================================
def supervisor_agent_node(state: SupervisorState) -> SupervisorState:
    print("\n🧠 Supervisor Agent: Starting Event-Driven CRM Workflow...\n")

    # -------------------------------------------------
    # Step 1️⃣ Load Companies & Run Recruitment Agent
    # -------------------------------------------------
    print("🧩 [1/4] Running Recruitment Agent (Lead Discovery)...")
    companies = load_companies()
    recruit_state = {"companies": companies, "shortlisted": []}
    recruit_output = recruitment_graph.invoke(recruit_state)
    shortlisted = recruit_output.get("shortlisted", [])
    print(f"✅ Recruitment completed — {len(shortlisted)} leads shortlisted.\n")

    if not shortlisted:
        print("⚠️ No leads shortlisted — stopping workflow early.")
        return {
            "companies": companies,
            "shortlisted": [],
            "emails_sent": [],
            "responses": [],
            "scheduled_meetings": [],
            "transcripts": [],
            "analyses": [],
        }

    # -------------------------------------------------
    # Step 2️⃣ Run Interaction Agent (async)
    # -------------------------------------------------
    print("💬 [2/4] Launching Interaction Agent (Email Outreach)...")
    interaction_state: Dict[str, Any] = {
        "shortlisted": shortlisted,
        "emails_sent": [],
        "responses": [],
    }

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    interaction_output = loop.run_until_complete(run_interaction_agent(interaction_state))
    loop.close()

    emails_sent = interaction_output.get("emails_sent", [])
    responses = interaction_output.get("responses", [])

    # Clean / normalize replies
    for r in responses:
        val = r.get("reply")
        if isinstance(val, str) and val.strip().lower() in ["none", "null", ""]:
            r["reply"] = None

    print(f"✅ Interaction completed — {len(responses)} responses recorded.\n")
    print("📨 Raw responses from Interaction Agent:")
    for r in responses:
        print(f"  - {r['email']} → status={r['status']} reply_snippet={str(r.get('reply'))[:80]}")

    # -------------------------------------------------
    # Step 3️⃣ Run Scheduler Agent ONLY if there are real replies
    # -------------------------------------------------
    print("\n📅 [3/4] Running Scheduler Agent (Meeting Scheduling, only if replies exist)...")
    valid_replies = [r for r in responses if has_valid_reply(r)]

    if not valid_replies:
        print("⚠️ No valid customer replies detected yet — skipping Scheduler.")
        scheduled_meetings: List[Dict[str, Any]] = []
    else:
        print(f"📩 Detected {len(valid_replies)} valid replies — triggering Scheduler Agent.")
        scheduler_state: Dict[str, Any] = {
            "responses": valid_replies,
            "scheduled_meetings": [],
            "follow_ups_sent": [],
        }
        scheduler_output = scheduler_graph.invoke(scheduler_state)
        scheduled_meetings = scheduler_output.get("scheduled_meetings", [])
        print(f"✅ Scheduler completed — {len(scheduled_meetings)} meetings scheduled.\n")

    # -------------------------------------------------
    # Step 4️⃣ Run Analytics Agent (Demo: uses call_transcripts.json)
    # -------------------------------------------------
    print("📊 [4/4] Running Analytics Agent (Call Insights)...")
    analytics_state: Dict[str, Any] = {"transcripts": [], "analyses": []}
    if os.path.exists("call_transcripts.json"):
        with open("call_transcripts.json", "r", encoding="utf-8") as f:
            analytics_state["transcripts"] = json.load(f)

    analytics_output = analytics_graph.invoke(analytics_state)
    analyses = analytics_output.get("analyses", [])
    print(f"✅ Analytics completed — {len(analyses)} analyses generated.\n")

    print("🎯 Supervisor: End-to-end CRM Workflow Completed Successfully!\n")

    return {
        "companies": companies,
        "shortlisted": shortlisted,
        "emails_sent": emails_sent,
        "responses": responses,
        "scheduled_meetings": scheduled_meetings,
        "transcripts": analytics_output.get("transcripts", []),
        "analyses": analyses,
    }

# ==========================================================
# 🔗 LangGraph Setup
# ==========================================================
graph = StateGraph(SupervisorState)
graph.add_node("SupervisorAgent", supervisor_agent_node)
graph.set_entry_point("SupervisorAgent")
graph.add_edge("SupervisorAgent", END)
supervisor_graph = graph.compile()

# ==========================================================
# 🧪 Standalone run
# ==========================================================
if __name__ == "__main__":
    initial_state: SupervisorState = {
        "companies": [],
        "shortlisted": [],
        "emails_sent": [],
        "responses": [],
        "scheduled_meetings": [],
        "transcripts": [],
        "analyses": [],
    }
    result = supervisor_graph.invoke(initial_state)
    print("\n📦 FINAL SUPERVISOR STATE:")
    print(json.dumps(result, indent=2))
