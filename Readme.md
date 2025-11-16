# TechNova Multi‑Agent CRM System

This project is a fully automated **stateful multi‑agent CRM platform** built using **LangGraph, LangChain, FastAPI, SMTP/IMAP, and Google Calendar API**.  
A custom **Streamlit dashboard** provides an interactive UI for monitoring agents, approving actions, and demonstrating the workflow.

---

## 🚀 Project Overview

TechNova is a fictional AI‑driven consulting company that helps B2B clients modernize operations using AI, cloud, and MLOps.  
This CRM system automates the **entire customer acquisition pipeline**:

1. **Lead Discovery (Recruitment Agent)**  
   - Analyses synthetic dataset of potential customers.  
   - Assigns intent scores and shortlists top clients.

2. **Email Outreach (Interaction Agent)**  
   - Generates personalized email drafts using LLMs.  
   - Allows user to edit & approve emails in UI.  
   - Sends emails via Gmail SMTP.  
   - Continuously polls inbox via IMAP for replies.

3. **Scheduling (Scheduler Agent)**  
   - Extracts meeting availability from customer reply.  
   - Auto‑schedules meetings in Google Calendar.  
   - Sends real calendar invites.

4. **Call Analytics (Analytics Agent)**  
   - Ingests call transcript (demo uses synthetic one).  
   - Produces summary, key themes, pain points, next best action.  
   - Stores results in summary file.

5. **Supervisor Agent**  
   - Orchestrates full stateful workflow end‑to‑end.

6. **Streamlit UI**  
   - Shows each agent step clearly.  
   - Users manually approve key actions (email sending, scheduling).  
   - Real‑time inbox monitoring + activity logs.  

---

## 🛠️ Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

Minimum required libraries:
```
streamlit
langchain
langgraph
langchain-openai
google-api-python-client
python-dotenv
```

### 2. Configure Environment Variables
Create `.env` file:
```
SMTP_EMAIL=your-email@gmail.com
SMTP_PASS=your-app-password
IMAP_EMAIL=your-email@gmail.com
IMAP_PASS=your-app-password
OPENAI_API_KEY=your-openai-key
```

### 3. Google Calendar API Setup
- Go to Google Cloud Console  
- Enable **Calendar API**  
- Download OAuth **credentials.json**  
- Place it in your project root  
- First run will open browser to authenticate  
- Generates `token.json`

---

## ▶️ Running the App

### **Start Streamlit UI**
```bash
streamlit run streamlit_app.py
```

### **Run Supervisor Agent only**
```bash
python main.py
```

---

## 🤖 How It Works (Workflow Summary)

### **Recruitment Agent**
- Reads synthetic customer dataset
- Uses LLM to assign intent scores
- Produces ranked shortlist

### **Interaction Agent**
- Generates email drafts (editable in UI)
- Sends approved emails via SMTP
- Uses IMAP polling to detect replies

### **Scheduler Agent**
- Parses reply sentiment & availability
- Schedules meeting in Google Calendar
- Sends invite to customer

### **Analytics Agent**
- Takes call transcript (synthetic for demo)
- Extracts summary, key insights, action items
- Saves results in `summary.txt`

---

## 🎯 Features

| Feature | Description |
|--------|-------------|
| 🔍 Lead Analysis | AI ranking of client intent |
| ✉️ Email Automation | SMTP + LLM email drafts |
| 📬 Auto Reply Detection | IMAP inbox scanning |
| 📅 Meeting Scheduling | Google Calendar integration |
| 📊 Call Analysis | LLM-powered transcript analytics |
| 📟 Streamlit UI | Real‑time agent monitoring |

---

## 📦 Deliverables
- Fully functional streamlit dashboard  
- End‑to‑end multi‑agent CRM pipeline  
- Real email + calendar scheduling  
- Editable outreach drafts  
- Stateful orchestration logic  
- Synthetic datasets for lead discovery & transcripts  (Replace it with real data, use Crunchbase or LinkedIn APIs )

---

## 🏆 This Project Demonstrates
✔ Multi-agent orchestration with LangGraph  
✔ AI‑driven customer acquisition  
✔ Real email + calendar tool usage  
✔ Generative AI for outreach & analytics  
✔ Event-driven agent triggers  
✔ Production-like CRM workflow in Python  

---
