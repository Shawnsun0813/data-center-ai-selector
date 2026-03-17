# 🏭 Data Center AI Site Selector

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30%2B-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![PostGIS](https://img.shields.io/badge/PostGIS-Spatial_DB-336791?logo=postgresql&logoColor=white)](https://postgis.net/)
[![LangGraph](https://img.shields.io/badge/Architecture-LangGraph_Supervisor-00C8FF)](#)

A production-grade, Multi-Agent AI system designed to automate the billion-dollar decision of Data Center site selection. It replaces weeks of manual consultancy work with a 60-second autonomous evaluation pipeline.

The system evaluates raw coordinates against 6 critical pillars: **Power Capacity, Grid Stability, Live Weather (PUE), Carbon Intensity, Natural Disaster Risk, and Local Zoning.**

---

## 🚀 Features

- **Real-Time Data Pipeline**: 
  - ⚡ Scrapes active Interconnection Queues from **PJM and NYISO** grid operators to determine true available MVA.
  - 🗺️ Compresses gigabytes of state-wide municipal zoning Shapefiles into a high-performance **GeoParquet Spatial Database** for millisecond 100% accurate *Point-in-Polygon* zoning lookups.
  - ⛅ Integrates *Open-Meteo* live weather for dynamic Power Usage Effectiveness (PUE) modeling.
- **Multi-Agent Supervisor Pattern**:
  - Implements a sophisticated LLM routing architecture (supports Gemini & OpenAI).
  - Four specialized "Expert Agents" debate the findings:
    - 🚀 **Elon Musk**: Evaluates Physics, thermal dynamics, and first-principles grid efficiency.
    - 💰 **Warren Buffett**: Calculates 10-Year OPEX and margin of safety.
    - 🌍 **Bill Gates**: Assesses carbon intensity and long-term climate resilience.
    - 🎨 **Steve Jobs**: Evaluates partner optics, connectivity status, and brand premium.
- **Zero-Hallucination Mathematics**: Base feasibility scores (0-100) are explicitly calculated in deterministic Python (`core_engine/scoring_logic.py`). LLMs are strictly used for *insight generation* based on the exact quantitative data arrays provided to them in XML tags.
- **Decision Matrix Dashboard**: Pitch-deck quality Streamlit UI for comparing "Site A vs Site B" with auto-generated Executive Verdicts.

---

## ⚙️ Architecture

```mermaid
graph TD
    User([User Details / Lat+Lon]) --> Frontend[Streamlit Dashboard]
    Frontend --> Orchestrator{LangGraph Supervisor}
    
    subgraph Data Engine [Deterministic Data Pipeline]
        Orchestrator --> Pipeline[pipeline_aggregator.py]
        Pipeline --> PJM[pjm_nyiso_scraper.py]
        Pipeline --> GIS[zoning_gis_builder.py]
        Pipeline --> APIs[OSM / FEMA / USGS / Open-Meteo]
    end
    
    Data Engine --> ScoringEngine[Scoring & 10-Yr OPEX Logic]
    
    subgraph Multi-Agent LLM Panel
        ScoringEngine --> Agents[llm_interface.py]
        Agents --> A1(Physics Agent / Elon)
        Agents --> A2(Finance Agent / Buffett)
        Agents --> A3(Policy Agent / Gates)
        Agents --> A4(Narrative Agent / Jobs)
    end
    
    Agents --> Frontend
```

---

## 🛠️ Local Setup

### 1. Requirements
Ensure you have Python 3.10+ installed.

```bash
git clone https://github.com/your-username/data-center-ai-selector.git
cd data-center-ai-selector
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment Variables
Create a `.env` file in the root directory.

```ini
# Optional: For higher rate limits on EIA grid data
EIA_API_KEY=your_eia_api_key

# Optional: If you want to connect to a remote Oracle VM PostGIS database
# SSH_HOST=your_vm_ip
# SSH_USER=ubuntu
# SSH_PKEY_PATH=/path/to/key.pem
```
*Note: The Gemini and OpenAI LLM keys are inputted securely via the Streamlit UI Sidebar.*

### 3. Run the Application
```bash
streamlit run frontend_ui/app.py
```
The application will automatically detect if it is missing the NY/NJ/PA spatial databases and queue data, and will bootstrap the scraper and `GeoParquet` compiler on first run.

---

## 🧠 Why Build This? (The Engineering Behind the Demo)

Anyone can wrap an LLM prompt around a coordinate. This project was built to prove that AI Agents are only as valuable as the **Data Engines** they are attached to. 

By replacing "simulated LLM coordinates" with actual scraping of the **PJM Grid Interconnection Queue** and utilizing **Geopandas** to compress multi-gigabyte government Shapefiles into instant spatial queries, this platform bridges the gap between a "Toy AI Demo" and a deployable enterprise tool.

---
*Built as a Proof of Concept for Autonomous Real Estate & Infrastructure Advisory.*
