import os
import json
from datetime import datetime
import sys

# -----------------------------------------
# ✅ Add Agents folder to Python path
# -----------------------------------------
sys.path.append(os.path.join(os.path.dirname(__file__), "Agents"))

from supervisor_agent import supervisor_graph  # Import the Supervisor Agent pipeline

# -----------------------------------------
# 🚀 Main Orchestrator
# -----------------------------------------
def main():
    print("\n🤖 Starting TechNova Multi-Agent CRM System...\n")

    # Initialize empty pipeline state
    initial_state = {
        "companies": [],
        "shortlisted": [],
        "emails_sent": [],
        "responses": [],
        "scheduled_meetings": [],
        "transcripts": [],
        "analyses": []
    }

    # -----------------------------------------
    # 🧠 Run Supervisor Agent (Full Pipeline)
    # -----------------------------------------
    final_state = supervisor_graph.invoke(initial_state)

    # -----------------------------------------
    # 💾 Save Output Files
    # -----------------------------------------
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = f"results_{timestamp}.json"

    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(final_state, f, indent=2)

    print(f"\n✅ Workflow complete!")
    print(f"📦 Full pipeline results saved to: {result_file}")
    print(f"📝 Detailed analytics written to: summary.txt\n")

    # Optional: Print a short report to console
    if final_state.get("analyses"):
        print("📈 Final Analytics Summary:")
        for a in final_state["analyses"]:
            print(f"- {a['_meta']['company_name']}: {a['sentiment']} — {a['summary'][:120]}...")
    else:
        print("⚠️ No analytics generated (no calls scheduled).")

# -----------------------------------------
# 🏁 Entry Point
# -----------------------------------------
if __name__ == "__main__":
    main()
