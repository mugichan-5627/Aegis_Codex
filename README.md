# Doomsday Rapid Agent ☢️

**A Google Cloud Rapid Agent Hackathon Submission**

⚡ **Live Streamlit Dashboard:** [doomsday-rapid-agent.streamlit.app](https://doomsday-rapid-agent.streamlit.app/)

Doomsday Rapid Agent is an executive-level adversarial threat simulator. Built as a high-velocity offshoot of the broader **Project Doomsday** initiative, this specialized platform features a multi-agent "Fracture Swarm" powered by **Gemini 3**, grounded in real-time with **Elastic MCP**, and fully observable via **Arize MCP** — all wrapped in a sleek, military-grade Geopolitical Risk Dashboard.

---

## ⚡ The Doomsday Offshoot Advancements

While carrying the DNA of the original Project Doomsday, the **Doomsday Rapid Agent** introduces fundamental structural and mathematical enhancements optimized for rapid decision cycles:

1. **Upgraded Swarm Logic (`agent_swarm.py`)**: 
   Introduces dynamic multi-agent adversarial debate rounds. The Geopolitical, Supply Chain, and Financial agents participate in a structured dialectic tribunal. They present rapid bull/bear arguments before the Black Swan Judge (Synthesizer) renders a finalized severity consensus.
2. **Enhanced Valuation Mathematics (`valuation_engine.py`)**:
   Rewrites the systemic degradation engine. Modern enterprise valuation models (Multi-Factor DCF, Cyclical, EV/Revenue) are devalued dynamically based on chaos parameters. The engine projects WACC degradation, direct revenue haircuts, and structural margin compression (BPS haircuts) directly into distress waterfalls.
3. **Advanced Telemetry Observability (`arize_mcp_client.py`)**:
   First-class tracing, evaluation, and latency logging. Tracks nested prompt latencies, model parameters, and raw chain-of-thought outputs back to Arize Phoenix.

---

## 🏗️ Architecture & Technology Stack

The platform is designed around a clean, decoupled agentic architecture:

1. **The Executive Cockpit (`app.py`)**: A Streamlit dashboard that visualizes the risk terrain using a dynamic **Plotly Mapbox Spoke-and-Hub Geopolitical Map**.
2. **The Valuation Router (`valuation_engine.py`)**: Automatically routes structural financials into the most appropriate mathematical model and calculates distressed WACC.
3. **The Fracture Swarm (`agent_swarm.py`)**: A multi-agent framework orchestrating high-velocity debates.

### 🔌 Partner MCP Integrations

*   **Elastic Model Context Protocol (MCP)**: The agents ground their severity scores and probability matrix calculations by querying macro indices and unstructured intelligence feeds stored in Elasticsearch via `elastic_mcp_client.py`.
*   **Arize Phoenix MCP**: Logs every step of the multi-agent debate—including token cost, latency, and chain-of-thought retrieval—to Arize Phoenix via `arize_mcp_client.py`.

---

## 🔑 Observability & API Key Setup (Arize Phoenix)

To make deploying and running this project as seamless as possible, the observability system features **Graceful Degradation Logic**:

*   **No Collector Required (Default)**: If no Arize Phoenix credentials or collector endpoints are detected, the system **automatically falls back to local dashboard logging**. The visual logs stream directly to the local UI console, allowing anyone to run the dashboard out-of-the-box without signup!
*   **Active Telemetry Configuration**: If you wish to pipe trace graphs to your Arize Cloud space or a local Phoenix server:
    *   **Via Environment Variables**: Define `PHOENIX_API_KEY` (or `ARIZE_API_KEY`) and `PHOENIX_COLLECTOR_ENDPOINT` in your local `.env` file.
    *   **Via Sidebar Console**: Expand the **"API CONFIG"** card directly in the Streamlit sidebar to enter your active Phoenix key and endpoint dynamically. The telemetry client will dynamically re-initialize and begin shipping trace spans instantly!

---

## 🚀 Quickstart Guide

### Prerequisites
- Python 3.10+
- A Google Gemini API Key (or Nvidia NIM / Fireworks API key)
- (Optional) Arize Phoenix API Key for cloud tracing
- (Optional) Elastic Cloud credentials for live data retrieval

### Installation
```bash
# Clone the repository
git clone https://github.com/mugichan-5627/Doomsday-Rapid-Agent.git
cd Doomsday_Rapid_Agent

# Install the required dependencies
pip install -r requirements.txt
```

### Running the Executive Cockpit
Deploy the Streamlit dashboard locally:
```bash
python -m streamlit run app.py
```
*The dashboard will automatically open in your default browser at `http://localhost:8501`.*

---

## 💡 How to Use
1. **Target Acquisition**: Input the target company ticker, baseline financials (Revenue, Debt, Margins), and HQ location in the sidebar's **RAPID AGENT CONSOLE**.
2. **Chaos Injector**: Slide the Global Chaos Index (0.0 to 1.0) to set the severity of the macro environment.
3. **Execute Protocol**: Hit "LAUNCH ANALYSIS" to trigger the Fracture Swarm. Watch as the agents debate the most critical risks, ground them in real-world geospatial nexuses, and devalue the enterprise value in real-time.

---
*Built for the Google Cloud Rapid Agent Hackathon.*
