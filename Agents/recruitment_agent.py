from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import BaseOutputParser
import json
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

# ===========================================
# ⚙️ Step 1: Define State Schema
# ===========================================
from typing import TypedDict, List, Dict, Any

class RecruitmentState(TypedDict):
    companies: List[Dict[str, Any]]
    shortlisted: List[Dict[str, Any]]

# ===========================================
# ⚙️ Step 2: Custom Parser for Intent Scores
# ===========================================
class IntentScoreParser(BaseOutputParser):
    """Parse model output into structured JSON."""
    def parse(self, text: str) -> List[Dict[str, Any]]:
        # Remove Markdown code fences if present
        text = text.strip()
        if text.startswith("```"):
            # Remove lines like ```json and ```
            text = "\n".join([
                line for line in text.splitlines()
                if not line.strip().startswith("```")
            ]).strip()

        try:
            data = json.loads(text)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass
        
        # Fallback for semi-structured output
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        results = []
        for line in lines:
            if ":" in line:
                try:
                    name, score = line.split(":")
                    results.append({
                        "company_name": name.strip(),
                        "intent_score": float(score.strip())
                    })
                except:
                    continue
        return results

# ===========================================
# ⚙️ Step 3: Load Synthetic Dataset
# ===========================================
def load_companies(file_path: str = "synthetic_clients.json") -> List[Dict[str, Any]]:
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

# ===========================================
# ⚙️ Step 4: Define LLM and Prompt
# ===========================================
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.0
)

prompt_template = PromptTemplate(
    input_variables=["company_list"],
    template=(
        "You are an AI recruitment analyst working for TechNova Consulting, "
        "an IT consulting firm specializing in cloud computing, cloud migration, data analytics, AI.\n"
        "Given the following companies with descriptions, assign an 'intent_score' (0–1) "
        "representing how likely they are to need TechNova's consulting services.\n"
        "Return output as a JSON list like:\n"
        "[{{'company_name': '...', 'intent_score': 0.87}}, ...]\n\n"
        "Companies:\n{company_list}"
    ),
)

# ===========================================
# ⚙️ Step 5: Define Recruitment Agent Node
# ===========================================
def recruitment_agent_node(state: RecruitmentState) -> RecruitmentState:
    """Uses LLM to compute intent scores and shortlist top clients."""
    companies = state["companies"]

    # Convert list to readable string for the LLM
    company_str = "\n".join([
        f"{c['company_name']}: {c['company_description']}" for c in companies
    ])

    prompt = prompt_template.format(company_list=company_str)
    parser = IntentScoreParser()

    response = llm.invoke(prompt)
    scores = parser.parse(response.content)

    # Merge scores with original metadata
    for company in companies:
        match = next((s for s in scores if s["company_name"].lower() in company["company_name"].lower()), None)
        if match:
            company["intent_score"] = match["intent_score"]

    # Sort and shortlist
    ranked = sorted(companies, key=lambda x: x.get("intent_score", 0), reverse=True)
    shortlisted = ranked[:2]  # top 3 leads

    return {"companies": companies, "shortlisted": shortlisted}

# ===========================================
# ⚙️ Step 6: Build LangGraph Workflow
# ===========================================
graph = StateGraph(RecruitmentState)
graph.add_node("RecruitmentAgent", recruitment_agent_node)
graph.set_entry_point("RecruitmentAgent")
graph.add_edge("RecruitmentAgent", END)

recruitment_graph = graph.compile()

# ===========================================
# ⚙️ Step 7: Run the Agent
# ===========================================
if __name__ == "__main__":
    companies = load_companies()

    initial_state = {
        "companies": companies,
        "shortlisted": []
    }

    final_state = recruitment_graph.invoke(initial_state)

    print("\n🏆 Top Shortlisted Clients:\n")
    df = pd.DataFrame(final_state["shortlisted"])
    print(df[["company_name", "intent_score", "industry", "location", "contact_email"]])
