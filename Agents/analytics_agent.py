import os
import json
from typing import TypedDict, List, Dict, Any
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langgraph.graph import StateGraph, END

# ==========================================================
# 1️⃣ Setup
# ==========================================================
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class AnalyticsState(TypedDict):
    transcripts: List[Dict[str, Any]]
    analyses: List[Dict[str, Any]]

# ==========================================================
# 2️⃣ LLM Setup
# ==========================================================
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2, api_key=OPENAI_API_KEY)

analysis_prompt = PromptTemplate(
    input_variables=["company_name", "industry", "transcript_text"],
    template=(
        "You are an expert meeting analyst at TechNova Consulting.\n"
        "Analyze the following transcript from a discovery call between a TechNova representative and a potential client.\n\n"
        "Return ONLY valid JSON with these keys:\n"
        "1. summary - concise summary of the call (2–3 sentences)\n"
        "2. top_themes - list of main topics discussed\n"
        "3. pain_points - list of explicit customer pain points\n"
        "4. next_best_actions - list of actionable follow-ups for TechNova\n"
        "5. sentiment - overall tone (Positive / Neutral / Negative)\n"
        "6. notable_quotes - up to 3 short quotes from the call\n\n"
        "Company: {company_name} ({industry})\n\n"
        "Transcript:\n{transcript_text}\n"
    )
)

# ==========================================================
# 3️⃣ Analytics Node
# ==========================================================
def analytics_agent_node(state: AnalyticsState) -> AnalyticsState:
    transcripts = state.get("transcripts", [])
    analyses = []

    for t in transcripts:
        prompt = analysis_prompt.format(
            company_name=t["company_name"],
            industry=t["industry"],
            transcript_text=t["transcript_text"]
        )

        response = llm.invoke(prompt)
        content = response.content.strip()

        # --- JSON parsing with fallback ---
        try:
            data = json.loads(content)
        except Exception:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end != -1:
                data = json.loads(content[start:end])
            else:
                data = {
                    "summary": "Parsing failed.",
                    "top_themes": [],
                    "pain_points": [],
                    "next_best_actions": [],
                    "sentiment": "Neutral",
                    "notable_quotes": []
                }

        data["_meta"] = {
            "company_name": t["company_name"],
            "industry": t["industry"]
        }
        analyses.append(data)

    # --- Save output to summary.txt ---
    with open("summary.txt", "w", encoding="utf-8") as f:
        for a in analyses:
            f.write(f"=== {a['_meta']['company_name']} ({a['_meta']['industry']}) ===\n")
            f.write(f"Sentiment: {a['sentiment']}\n")
            f.write(f"Summary: {a['summary']}\n\n")
            f.write("Top Themes:\n  - " + "\n  - ".join(a["top_themes"]) + "\n")
            f.write("Pain Points:\n  - " + "\n  - ".join(a["pain_points"]) + "\n")
            f.write("Next Best Actions:\n  - " + "\n  - ".join(a["next_best_actions"]) + "\n")
            f.write("Notable Quotes:\n  - " + "\n  - ".join(a["notable_quotes"]) + "\n\n")
            f.write("=" * 60 + "\n\n")

    print("📝 Analytics summary written to 'summary.txt'")
    return {"transcripts": transcripts, "analyses": analyses}

# ==========================================================
# 4️⃣ LangGraph Setup
# ==========================================================
graph = StateGraph(AnalyticsState)
graph.add_node("AnalyticsAgent", analytics_agent_node)
graph.set_entry_point("AnalyticsAgent")
graph.add_edge("AnalyticsAgent", END)
analytics_graph = graph.compile()

# ==========================================================
# 5️⃣ Run Demo
# ==========================================================
if __name__ == "__main__":
    # Load transcript(s)
    with open("call_transcripts.json", "r", encoding="utf-8") as f:
        transcripts = json.load(f)

    state = {"transcripts": transcripts, "analyses": []}
    result = analytics_graph.invoke(state)

    print("\n📈 ANALYTICS SUMMARY (console preview):\n")
    for a in result["analyses"]:
        print(f"=== {a['_meta']['company_name']} ({a['_meta']['industry']}) ===")
        print(f"Sentiment: {a['sentiment']}")
        print(f"Summary: {a['summary']}\n")
