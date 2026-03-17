# Data Center Site Selection Assessment Tool - Implementation Plan

## Problem Description
The goal is to build a robust, Python-based evaluation tool to help stakeholders select optimal locations for new data centers. The tool will integrate geographical, financial, and infrastructure data to provide a weighted ranking of potential sites.

## Proposed Changes

### [Component] Architecture & Tech Stack
- **Languages**: Python 3.10+
- **Frontend**: Streamlit (Dashboard & Visualization)
- **Mapping**: Folium / Plotly Mapbox
- **Data Handling**: Pandas, GeoPandas
- **Calculations**: NumPy, SciPy
- **Agent Framework**: LangGraph / Supervisor Pattern (Custom implemented)

---

### [Component] Multi-Agent Coordination Layer
This layer acts as the orchestrator (Supervisor) to manage state and handoffs between specialized agents.

#### [NEW] `orchestrator.py` (file:///c:/Users/archi/OneDrive/Desktop/Winter%20Project/Multi_agent/Site%20selection/New_type_project/orchestrator.py)
**Functionality**:
- **DataScoutAgent**: Wraps `data_pipeline` to fetch and aggregate raw site metrics.
- **ScoringAnalystAgent**: Wraps `core_engine` to perform weighted scoring and risk analysis.
- **DecisionSupportAgent**: Bridges findings to the `frontend_ui` for executive review.

**States Managed**:
- `SiteCollection`: List of raw site data.
- `EvaluationResults`: Scored sites with rationale.
- `FinalDecisionBrief`: Summary for the dashboard.

---

### [Component] Module 1: Data Acquisition (Data Engine)
This module is responsible for gathering and normalizing data from various sources (OpenStreetMap, World Bank, Energy APIs, or local CSVs).

#### [MODIFY] `data_pipeline/pipeline_aggregator.py`(file:///c:/Users/archi/OneDrive/Desktop/Winter%20Project/Multi_agent/Site%20selection/New_type_project/data_pipeline/pipeline_aggregator.py)
**Functionality**:
- Fetch grid stability and energy cost data.
- Retrieve natural disaster risk profiles.
- Parse connectivity (fiber backbone) proximity.
- **NEW**: Replace simulated `power_capacity.py` with the output from `pjm_nyiso_scraper.py` (Local CSV cache -> query nearest substation).
- **NEW**: Replace simulated `zoning.py` with spatial queries against `zoning_gis_builder.py`'s GeoParquet database.

**Interfaces**:
- **Input**: `LocationQuery` (List of regions/cities, coordinates)
- **Output**: `DataSet` (A structured DataFrame/GeoJSON with normalized values for: Energy Cost, Connectivity, Disaster Risk, Tax Incentives, Water Access).

---

### [Component] Module 2: Core Algorithm (Logic Hub)
The brain of the tool that processes the raw data into actionable insights using weighted scoring.

#### [NEW] `logic_hub.py` (file:///C:/Users/archi/.gemini/antigravity/playground/ionized-sagan/logic_hub.py)
**Functionality**:
- Implement Multi-Criteria Decision Analysis (MCDA).
- Calculate normalized scores based on user-defined weights.
- Perform sensitivity analysis (what happens if energy cost increases by 20%?).

**Interfaces**:
- **Input**: 
  - `LocationData` (from Data Engine)
  - `UserWeights` (Dictionary: `{"Energy": 0.4, "Latency": 0.3, ...}`)
- **Output**: 
  - `ScoredSites` (Sorted list of locations with breakdown)
  - `RiskMatrix` (Assessment of catastrophic risks)

---

### [Component] Module 3: Streamlit Frontend (Control Center)
The interactive interface for decision-makers.

#### [NEW] `app.py` (file:///C:/Users/archi/.gemini/antigravity/playground/ionized-sagan/app.py)
**Functionality**:
- Sidebar widgets for weight adjustment (0-100%).
- Interactive map visualization (color-coded by score).
- Comparison view (Side-by-side site analysis).
- Export functionality (PDF/CSV report).

**Interfaces**:
- **Input**: User inputs via Streamlit widgets.
- **Output**: Visualized Dataframes, Charts, and Interactive Maps.

## Verification Plan

### Automated Tests
- Unit tests for `logic_hub.py` to ensure weighted scores sum correctly and normalization is consistent.
- Mock data tests for `data_engine.py` to verify schema consistency.

### Manual Verification
- **Functional Check**: Adjust energy cost weight in Streamlit sidebar and verify if locations with high energy costs drop in the rankings instantly.
- **Visual Check**: Ensure the map correctly displays tooltips with site-specific attributes.
- **Export Check**: Download a generated report and verify it contains all critical metrics.

## Design Philosophy (Skills Applied)
- **Product Manager**: Focus on "Jobs-to-be-Done" (Decision making) and "Opportunity Scoring".
- **Startup Analyst**: Emphasis on unit economics and energy trends.
- **Warren Buffett**: Risk-adjusted returns and margin of safety in site selection.
- **Elon Musk**: First-principles analysis of power density and cooling efficiency.
