import streamlit as st
import pandas as pd
import numpy as np
import sys
import os
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

# Add parent directory to sys.path to find orchestrator
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Geocoder (cached so we don't re-instantiate on every rerun) ──
@st.cache_resource
def get_geocoder():
    return Nominatim(user_agent="datacenter_site_selection_v1", timeout=5)

@st.cache_data(ttl=3600)
def geocode_place(place_name: str):
    """Forward geocoding: city name → (lat, lon, display_name)"""
    try:
        geo = get_geocoder()
        loc = geo.geocode(place_name)
        if loc:
            return loc.latitude, loc.longitude, loc.address
    except (GeocoderTimedOut, GeocoderServiceError):
        pass
    return None, None, None

@st.cache_data(ttl=3600)
def reverse_geocode(lat: float, lon: float):
    """Reverse geocoding: (lat, lon) → city/address string"""
    try:
        geo = get_geocoder()
        loc = geo.reverse((lat, lon), language="en")
        if loc:
            addr = loc.raw.get("address", {})
            # Build a concise city label
            city = (addr.get("city") or addr.get("town") or addr.get("village")
                    or addr.get("county") or addr.get("state") or "")
            state = addr.get("state", "")
            country = addr.get("country_code", "").upper()
            parts = [p for p in [city, state, country] if p]
            return ", ".join(parts) or loc.address[:60]
    except (GeocoderTimedOut, GeocoderServiceError):
        pass
    return ""

st.set_page_config(
    page_title="Data Center Site Selection AI",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Template CSS: white bg, bold headers, cyan accents, monospace ──
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=Space+Mono:wght@400;700&display=swap');

    /* ── Base App ── */
    .stApp {
        background-color: #ffffff;
        color: #111111;
        font-family: 'Space Mono', monospace;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background-color: #f5f5f5;
        border-right: 2px solid #111111;
    }
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #111111 !important;
        font-family: 'Space Mono', monospace !important;
    }
    /* Explicitly protect icons/svgs from any potential accidental override */
    [data-testid="stSidebar"] svg,
    [data-testid="stSidebar"] i,
    [data-testid="stIcon"] {
        font-family: inherit !important;
    }

    /* ── Main Title ── */
    h1, .main-title {
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 800 !important;
        text-transform: uppercase !important;
        letter-spacing: 2px !important;
        color: #111111 !important;
        font-size: 2.4rem !important;
    }

    /* ── Subtitles ── */
    h2, h3 {
        font-family: 'Space Mono', monospace !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        color: #111111 !important;
        letter-spacing: 1px !important;
    }

    /* ── Cyan accent text ── */
    .cyan { color: #00c8ff; font-family: 'Space Mono', monospace; }
    .accent-label {
        color: #00c8ff !important;
        font-family: 'Space Mono', monospace !important;
        font-size: 0.78rem !important;
        letter-spacing: 1px !important;
        text-transform: uppercase !important;
    }

    /* ── Metric cards ── */
    [data-testid="metric-container"] {
        background: #f8f8f8;
        border: 1px solid #cccccc;
        border-left: 3px solid #00c8ff;
        padding: 16px 20px;
        border-radius: 0;
        transition: border-left-color 0.25s;
    }
    [data-testid="metric-container"]:hover {
        border-left-color: #111111;
        background: #f0f0f0;
    }
    [data-testid="metric-container"] label {
        font-family: 'Space Mono', monospace !important;
        font-size: 0.7rem !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        color: #888888 !important;
    }
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 800 !important;
        font-size: 1.6rem !important;
        color: #111111 !important;
    }

    /* ── Buttons ── */
    .stButton > button {
        background-color: #111111 !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 0 !important;
        font-family: 'Space Mono', monospace !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        padding: 10px 28px !important;
        transition: background-color 0.2s ease;
    }
    .stButton > button:hover {
        background-color: #00c8ff !important;
        color: #111111 !important;
    }

    /* ── Tables ── */
    table {
        color: #111111 !important;
        background-color: #ffffff !important;
        border-collapse: collapse !important;
        font-family: 'Space Mono', monospace !important;
        font-size: 0.82rem !important;
        width: 100% !important;
    }
    thead tr th {
        color: #111111 !important;
        background-color: #f5f5f5 !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        border-bottom: 2px solid #111111 !important;
        padding: 10px 14px !important;
        font-size: 0.72rem !important;
    }
    tbody tr td {
        color: #222222 !important;
        border-bottom: 1px solid #eeeeee !important;
        padding: 10px 14px !important;
    }
    tbody tr:hover td {
        background-color: #f8f8f8 !important;
    }
    /* Cyan for numeric highlights in first td col */
    tbody tr td:first-child {
        color: #111111 !important;
        font-weight: 600 !important;
    }

    /* ── Info / Alert boxes ── */
    [data-testid="stInfo"] {
        background-color: #f0fbff !important;
        border-left: 3px solid #00c8ff !important;
        border-radius: 0 !important;
        color: #111111 !important;
        font-family: 'Space Mono', monospace !important;
        font-size: 0.82rem !important;
    }
    [data-testid="stSuccess"] {
        background-color: #f0fff4 !important;
        border-left: 3px solid #111111 !important;
        border-radius: 0 !important;
        color: #111111 !important;
        font-family: 'Space Mono', monospace !important;
    }

    /* ── Tabs ── */
    [data-testid="stTabs"] button {
        font-family: 'Space Mono', monospace !important;
        text-transform: uppercase !important;
        font-weight: 700 !important;
        font-size: 0.78rem !important;
        letter-spacing: 1px !important;
        color: #888888 !important;
    }
    [data-testid="stTabs"] button[aria-selected="true"] {
        color: #111111 !important;
        border-bottom: 2px solid #00c8ff !important;
    }

    /* ── Inputs ── */
    input, .stTextInput input, .stNumberInput input {
        border-radius: 0 !important;
        border: 1px solid #cccccc !important;
        font-family: 'Space Mono', monospace !important;
        font-size: 0.85rem !important;
        color: #111111 !important;
        background-color: #ffffff !important;
    }

    /* ── Divider ── */
    hr { border-top: 2px solid #111111; }

    /* ── Corner brackets (decorative) ── */
    .bracket-box {
        position: relative;
        padding: 28px 32px;
        margin-bottom: 24px;
    }
    .bracket-box::before,
    .bracket-box::after {
        content: '';
        position: absolute;
        width: 18px;
        height: 18px;
        border-color: #111111;
        border-style: solid;
    }
    .bracket-box::before { top: 0; left: 0; border-width: 2px 0 0 2px; }
    .bracket-box::after  { bottom: 0; right: 0; border-width: 0 2px 2px 0; }

    /* ── Expander ── */
    div[data-testid="stExpander"] {
        border: 1px solid #cccccc !important;
        border-radius: 0 !important;
        background: #fafafa !important;
    }
    div[data-testid="stExpander"] summary {
        font-family: 'Space Mono', monospace !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        font-size: 0.78rem !important;
    }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-thumb { background: #cccccc; }
    /* ── Radar Animation ── */
    .radar-container {
        position: relative;
        width: 100%;
        height: 300px;
        background: #fdfdfd;
        border: 1px solid #111111;
        overflow: hidden;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .radar-pulse {
        position: absolute;
        width: 10px;
        height: 10px;
        background: #00c8ff;
        border-radius: 50%;
        animation: radar-pulse 3s infinite linear;
    }
    .radar-scan-line {
        position: absolute;
        width: 100%;
        height: 2px;
        background: linear-gradient(to bottom, transparent, #00c8ff, transparent);
        top: 0;
        animation: radar-scan 2.5s infinite linear;
    }
    @keyframes radar-pulse {
        0% { transform: scale(1); opacity: 0.8; }
        100% { transform: scale(30); opacity: 0; }
    }
    @keyframes radar-scan {
        0% { top: 0%; }
        100% { top: 100%; }
    }
    .radar-label {
        font-family: 'Space Mono', monospace;
        text-transform: uppercase;
        font-weight: 700;
        color: #111111;
        z-index: 10;
        background: rgba(255,255,255,0.8);
        padding: 5px 15px;
    }
    </style>
""", unsafe_allow_html=True)

# Import the Orchestrator and force a reload to pick up live code changes
import importlib
import orchestrator
importlib.reload(orchestrator)
from orchestrator import SiteSelectionSupervisor
# Always create a fresh supervisor to pick up latest code changes
st.session_state.supervisor = SiteSelectionSupervisor()

# Import recommendation engine
import core_engine.recommendation_engine as rec_engine
importlib.reload(rec_engine)
from core_engine.recommendation_engine import recommend_hotspots

def run_analysis(lat, lon, weights, llm_config=None):
    targets = [(lat, lon)]
    results = st.session_state.supervisor.execute_workflow(targets, weights=weights, llm_config=llm_config)
    if not results.empty:
        return results.iloc[0]
    return None

# ── Corner bracket header helper ──
def section_header(title, subtitle=""):
    st.markdown(f"""
    <div class="bracket-box">
        <h2 style="margin:0 0 4px 0">{title}</h2>
        {"<p class='cyan' style='margin:0;font-family:Space Mono,monospace;font-size:0.9rem'>" + subtitle + "</p>" if subtitle else ""}
    </div>
    """, unsafe_allow_html=True)

def main():
    # ── LLM API Config (Sidebar) ──
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 🔑 AI Specialist Config")
        st.caption("Connect a real LLM to generate live expert rationales.")
        llm_provider = st.selectbox(
            "Provider",
            ["None (Rule-based)", "Google Gemini", "OpenAI GPT-4o"],
            key="llm_provider"
        )
        llm_api_key = ""
        if llm_provider != "None (Rule-based)":
            llm_api_key = st.text_input(
                "API Key",
                type="password",
                placeholder="Paste your key here...",
                key="llm_api_key"
            )
            if llm_provider == "Google Gemini":
                st.caption("[Get Gemini API key →](https://aistudio.google.com/apikey)")
            else:
                st.caption("[Get OpenAI API key →](https://platform.openai.com/api-keys)")
        
        provider_map = {
            "Google Gemini": "gemini",
            "OpenAI GPT-4o": "openai",
            "None (Rule-based)": ""
        }
        llm_config = {
            "provider": provider_map.get(llm_provider, ""),
            "api_key": llm_api_key
        }
        if llm_api_key:
            st.success("✅ PRO TIER ACTIVE")
        else:
            st.warning("🔒 PRO TIER LOCKED")
            st.info("ℹ️ Using rule-based fallback. Upgrade to Pro for autonomous AI rationales.")
        st.markdown("---")

    # ── Page Title ──
    st.markdown("""
    <h1 style='font-family:"Space Grotesk",sans-serif;font-weight:800;
               text-transform:uppercase;letter-spacing:2px;color:#111;margin-bottom:4px'>
        Data Center Site Selection
    </h1>
    <p class='cyan' style='font-family:"Space Mono",monospace;font-size:0.95rem;margin-bottom:0'>
        AI-Powered Multi-Agent Intelligence Platform
    </p>
    """, unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Sidebar ──
    st.sidebar.markdown("### ⚖️ EVALUATION WEIGHTS")
    st.sidebar.markdown("<small style='color:#888'>Adjust the priorities of the expert panel.</small>", unsafe_allow_html=True)
    st.sidebar.markdown("---")

    weights = {
        "Power":        st.sidebar.slider("Energy & Physical Efficiency", 0, 100, 40) / 100,
        "Connectivity": st.sidebar.slider("Connectivity & Latency",         0, 100, 30) / 100,
        "Land":         st.sidebar.slider("Sustainability & Risk Profile",   0, 100, 20) / 100,
        "Financials":   st.sidebar.slider("Financial Moat & Incentives",   0, 100, 10) / 100,
    }

    total = sum(weights.values())
    if total > 0:
        weights = {k: v / total for k, v in weights.items()}

    st.sidebar.markdown("---")
    st.sidebar.markdown("**WEIGHT ALLOCATION**")
    for k, v in weights.items():
        st.sidebar.markdown(f"<span class='accent-label'>{k}</span> — {v*100:.0f}%", unsafe_allow_html=True)

    # ── Tabs ──
    tab1, tab2, tab3 = st.tabs(["SINGLE SITE ANALYSIS", "MULTI-SITE COMPARISON", "SMART REGION SEARCH"])

    # ════════════════════════════════════════════
    with tab1:
        section_header("SITE ASSESSMENT", "Input target coordinates and run the AI expert panel.")
        c_inp, c_map = st.columns([1, 2])
        with c_inp:
            # ── City Search (forward geocoding) ──
            st.markdown("<span class='accent-label'>🔍 Search by City / Address</span>", unsafe_allow_html=True)
            city_query = st.text_input(
                "City search", value="", placeholder="e.g. Ashburn, VA or Tokyo",
                key="city_search", label_visibility="collapsed"
            )
            if city_query.strip():
                with st.spinner("Looking up location..."):
                    glat, glon, gaddr = geocode_place(city_query.strip())
                if glat is not None:
                    st.session_state["lat1"] = float(glat)
                    st.session_state["lon1"] = float(glon)
                    st.session_state["resolved_addr"] = gaddr
                    st.markdown(
                        f"<div style='font-family:Space Mono,monospace;font-size:0.78rem;"
                        f"color:#00c8ff;margin:4px 0 8px'>"
                        f"✅ {gaddr[:80]}{'…' if len(gaddr)>80 else ''}</div>",
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        "<div style='font-family:Space Mono,monospace;font-size:0.78rem;color:#cc3333;margin:4px 0 8px'>"
                        "⚠️ Location not found — try a more specific name.</div>",
                        unsafe_allow_html=True
                    )

            st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)
            st.markdown("<span class='accent-label'>📍 Or Enter Coordinates Manually</span>", unsafe_allow_html=True)

            lat_default = st.session_state.get("lat1", 38.8048)
            lon_default = st.session_state.get("lon1", -77.0469)

            lat = st.number_input("Latitude",  value=float(lat_default), format="%.6f", key="lat1")
            lon = st.number_input("Longitude", value=float(lon_default), format="%.6f", key="lon1")

            # ── Reverse geocode as the user changes lat/lon ──
            nearby_city = reverse_geocode(lat, lon)
            if nearby_city:
                st.markdown(
                    f"<div style='font-family:Space Mono,monospace;font-size:0.78rem;"
                    f"color:#555555;border-left:3px solid #00c8ff;padding:4px 10px;"
                    f"margin:6px 0 10px'>📌 Nearest: <strong>{nearby_city}</strong></div>",
                    unsafe_allow_html=True
                )

            site_name = nearby_city or city_query or "Unnamed Site"
            analyze_btn = st.button("RUN AI ASSESSMENT", key="btn1")

        with c_map:
            map_data = pd.DataFrame({'lat': [lat], 'lon': [lon]})
            st.map(map_data, zoom=8)

        if analyze_btn:
            st.markdown("<hr>", unsafe_allow_html=True)
            section_header(f"RESULTS — {site_name.upper()}", f"Lat {lat:.4f} / Lon {lon:.4f}")
            with st.spinner("Expert panel analysing site..."):
                res = run_analysis(lat, lon, weights, llm_config=llm_config)
                if res is not None:
                    # ── KPI Strip ──
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Feasibility Score",   f"{res['feasibility_score']:.1f} / 100")
                    m2.metric("Power Capacity",       f"{res['power_capacity_mw']:.0f} MW")
                    m3.metric("Grid Stability",        f"{res['grid_stability']*100:.0f}%")
                    m4.metric("Predicted PUE",         f"{res['predicted_pue']:.2f}")

                    m5, m6, m7, m8 = st.columns(4)
                    m5.metric("Carbon Intensity",      f"{res['carbon_intensity_gco2']:.0f} gCO₂/kWh")
                    m6.metric("10-Year OPEX",          f"${res['opex_10yr_m']:.1f}M")
                    m7.metric("Zoning",                res['zoning_type'])
                    m8.metric("Permit Status",         res['permit_status'])

                    # ── Address ──
                    if "address" in res and res["address"] not in ["Unknown Location", ""]:
                        st.info(f"📍 **Location:** {res['address']}")

                    # ── Specialist Panel — LIVE LLM or Rule-Based ──
                    st.markdown("<hr>", unsafe_allow_html=True)
                    st.markdown("### SPECIALIST PANEL INSIGHTS")
                    
                    using_llm = bool(llm_config.get("api_key"))
                    if using_llm:
                        st.markdown(f"<p class='cyan' style='font-size:0.85rem;font-family:Space Mono,monospace'>⚡ Live AI Rationale — {llm_config['provider'].upper()}</p>", unsafe_allow_html=True)
                        with st.spinner("Calling specialist LLMs..."):
                            live_r = st.session_state.supervisor.advisor.generate_live_rationales(
                                dict(res), llm_config
                            )
                        col_el, col_bu = st.columns(2)
                        with col_el:
                            st.success(f"🚀 **Elon Musk**\n\n{live_r['elon']}")
                            st.info(f"🌍 **Bill Gates**\n\n{live_r['gates']}")
                        with col_bu:
                            st.warning(f"💰 **Warren Buffett**\n\n{live_r['buffett']}")
                            st.error(f"🎨 **Steve Jobs**\n\n{live_r['jobs']}")
                    else:
                        st.markdown(
                            "<div style='background:#fff0f3; border:1px solid #ff4b4b; padding:15px; margin-bottom:15px'>"
                            "<h4 style='color:#ff4b4b; margin:0; font-family:Space Grotesk,sans-serif'>🔒 PRO TIER FEATURE</h4>"
                            "<p style='margin:5px 0 0; font-size:0.85rem'>Autonomous AI Expert Rationales are locked. "
                            "Upgrade to Pro & add API Key to unlock GPT-4o Insights.</p></div>", 
                            unsafe_allow_html=True
                        )
                        st.markdown("<p style='font-size:0.75rem; color:#888; font-family:Space Mono,monospace'>Falling back to Rule-Based Metrics Analysis:</p>", unsafe_allow_html=True)
                        rationales = res['rationale'].split(" | ")
                        expert_data = {
                            "Expert":   ["🚀 Elon Musk",     "💰 Warren Buffett", "🌍 Bill Gates",    "🎨 Steve Jobs"],
                            "Focus":    ["Physics / PUE",   "Unit Economics",    "Carbon & Policy",  "Edge Positioning"],
                            "Finding":  (rationales + ["—"] * 4)[:4],
                        }
                        st.table(pd.DataFrame(expert_data))

                    # ── Technical Spec ──
                    with st.expander("TECHNICAL SPECIFICATIONS"):
                        spec_df = pd.DataFrame({
                            "Parameter": ["Power Capacity", "Grid Stability", "Carbon Intensity", "Predicted PUE", "10-Year OPEX", "Zoning", "Permit Status"],
                            "Value":     [
                                f"{res['power_capacity_mw']:.1f} MW",
                                f"{res['grid_stability']*100:.0f}%",
                                f"{res['carbon_intensity_gco2']:.0f} gCO₂/kWh",
                                f"{res['predicted_pue']:.2f}",
                                f"${res['opex_10yr_m']:.1f}M",
                                res['zoning_type'],
                                res['permit_status'],
                            ],
                            "Source": [
                                "PJM / NYISO Real-time",
                                "Regional Utility Maps",
                                "Grid-level Carbon Track (Live)",
                                "Climate Data (NOAA)",
                                "Proprietary ROI Engine",
                                "NY/NJ/PA GIS Database",
                                "Local Municipal Records"
                            ]
                        })
                        st.table(spec_df)

    # ════════════════════════════════════════════
    with tab2:
        section_header("MULTI-SITE COMPARISON", "Side-by-side expert evaluation — AI-Driven Decision Matrix")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("<span class='accent-label'>Site A — City Search</span>", unsafe_allow_html=True)
            city_a = st.text_input("City A", value="", placeholder="e.g. Ashburn, VA", key="city_a", label_visibility="collapsed")
            if city_a.strip():
                glat_a, glon_a, _ = geocode_place(city_a.strip())
                if glat_a:
                    st.session_state["lat_a"] = float(glat_a)
                    st.session_state["lon_a"] = float(glon_a)
                    st.markdown(f"<div style='font-family:Space Mono,monospace;font-size:0.75rem;color:#00c8ff'>✅ Located</div>", unsafe_allow_html=True)
            lat_a = st.number_input("Lat A", value=float(st.session_state.get("lat_a", 39.0438)), format="%.6f", key="lat_a")
            lon_a = st.number_input("Lon A", value=float(st.session_state.get("lon_a", -77.4874)), format="%.6f", key="lon_a")
            city_label_a = reverse_geocode(lat_a, lon_a)
            name_a = city_label_a or city_a or "Site A"
            if city_label_a:
                st.markdown(f"<div style='font-family:Space Mono,monospace;font-size:0.75rem;color:#555;border-left:3px solid #00c8ff;padding:3px 8px'>📌 {city_label_a}</div>", unsafe_allow_html=True)

        with c2:
            st.markdown("<span class='accent-label'>Site B — City Search</span>", unsafe_allow_html=True)
            city_b = st.text_input("City B", value="", placeholder="e.g. New York, NY", key="city_b", label_visibility="collapsed")
            if city_b.strip():
                glat_b, glon_b, _ = geocode_place(city_b.strip())
                if glat_b:
                    st.session_state["lat_b"] = float(glat_b)
                    st.session_state["lon_b"] = float(glon_b)
                    st.markdown(f"<div style='font-family:Space Mono,monospace;font-size:0.75rem;color:#00c8ff'>✅ Located</div>", unsafe_allow_html=True)
            lat_b = st.number_input("Lat B", value=float(st.session_state.get("lat_b", 40.7128)), format="%.6f", key="lat_b")
            lon_b = st.number_input("Lon B", value=float(st.session_state.get("lon_b", -74.0060)), format="%.6f", key="lon_b")
            city_label_b = reverse_geocode(lat_b, lon_b)
            name_b = city_label_b or city_b or "Site B"
            if city_label_b:
                st.markdown(f"<div style='font-family:Space Mono,monospace;font-size:0.75rem;color:#555;border-left:3px solid #00c8ff;padding:3px 8px'>📌 {city_label_b}</div>", unsafe_allow_html=True)

        debate_btn = st.button("START AGENT DEBATE")

        if debate_btn:
            with st.spinner("Orchestrating expert comparison..."):
                res_a = run_analysis(lat_a, lon_a, weights)
                res_b = run_analysis(lat_b, lon_b, weights)

                if res_a is not None and res_b is not None:
                    # ROI Explosion Banner
                    delta_opex = res_a['opex_10yr_m'] - res_b['opex_10yr_m']
                    better_site = name_b if delta_opex > 0 else name_a
                    savings = abs(delta_opex)
                    
                    st.markdown(f"""
                    <div style="background: linear-gradient(90deg, #001f3f 0%, #00c8ff 100%); 
                                padding: 25px; border-radius: 0; color: white; margin: 20px 0;
                                border-left: 10px solid #111; box-shadow: 0 4px 15px rgba(0,200,255,0.3)">
                        <h3 style="color: white; margin: 0; font-family: 'Space Grotesk', sans-serif; letter-spacing: 2px;">🚀 ROI EXPLOSION</h3>
                        <p style="margin: 10px 0 0; font-family: 'Space Mono', monospace; font-size: 1.1rem;">
                            Choosing <strong>{better_site.upper()}</strong> over the alternative saves approximately 
                            <span style="font-size: 1.5rem; font-weight: 800; color: #fff;">${savings:.1f}M</span> 
                            in operational costs over the next 10 years.
                        </p>
                        <p style="margin: 5px 0 0; font-size: 0.75rem; opacity: 0.8;">[Supervisor Insight: ROI Optimization Mode Active]</p>
                    </div>
                    """, unsafe_allow_html=True)

                    st.markdown("<hr>", unsafe_allow_html=True)
                    st.markdown("### DECISION MATRIX")
                    st.markdown("<p class='cyan' style='font-size:0.85rem;font-family:Space Mono,monospace'>Weighted Scoring — Six-Pillar Assessment</p>", unsafe_allow_html=True)

                    # ── Comparison Table ──
                    winner_score = "✅" if res_a['feasibility_score'] >= res_b['feasibility_score'] else "—"
                    loser_score  = "—" if winner_score == "✅" else "✅"
                    metrics_rows = [
                        ("Feasibility Score",    f"{res_a['feasibility_score']:.1f}",              f"{res_b['feasibility_score']:.1f}"),
                        ("Power Capacity (MW)",  f"{res_a['power_capacity_mw']:.1f}",              f"{res_b['power_capacity_mw']:.1f}"),
                        ("Grid Stability",        f"{res_a['grid_stability']*100:.0f}%",            f"{res_b['grid_stability']*100:.0f}%"),
                        ("Predicted PUE",         f"{res_a['predicted_pue']:.2f}",                  f"{res_b['predicted_pue']:.2f}"),
                        ("Carbon (gCO₂/kWh)",    f"{res_a['carbon_intensity_gco2']:.0f}g",         f"{res_b['carbon_intensity_gco2']:.0f}g"),
                        ("10-Year OPEX",          f"${res_a['opex_10yr_m']:.1f}M",                  f"${res_b['opex_10yr_m']:.1f}M"),
                        ("Zoning",                res_a['zoning_type'],                              res_b['zoning_type']),
                        ("Permit Status",         res_a['permit_status'],                            res_b['permit_status']),
                    ]
                    cmp_df = pd.DataFrame(metrics_rows, columns=["METRIC", f"{name_a.upper()} (A)", f"{name_b.upper()} (B)"])
                    st.table(cmp_df)

                    # ── Agent Debate ──
                    st.markdown("<hr>", unsafe_allow_html=True)
                    st.markdown("### AGENT EXPERT DEBATE")
                    st.markdown("<p class='cyan' style='font-size:0.85rem;font-family:Space Mono,monospace'>Specialist Conflict Analysis — Site-Specific Reasoning</p>", unsafe_allow_html=True)

                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown(f"**{name_a.upper()}**")
                        for line in res_a['rationale'].split(" | "):
                            st.markdown(f"<div style='border-left:3px solid #00c8ff;padding:6px 12px;margin-bottom:8px;font-family:Space Mono,monospace;font-size:0.8rem;color:#111'>{line}</div>", unsafe_allow_html=True)
                    with col_b:
                        st.markdown(f"**{name_b.upper()}**")
                        for line in res_b['rationale'].split(" | "):
                            st.markdown(f"<div style='border-left:3px solid #00c8ff;padding:6px 12px;margin-bottom:8px;font-family:Space Mono,monospace;font-size:0.8rem;color:#111'>{line}</div>", unsafe_allow_html=True)

                    # ── Supervisor Verdict ──
                    winner = name_a if res_a['feasibility_score'] >= res_b['feasibility_score'] else name_b
                    margin = abs(res_a['feasibility_score'] - res_b['feasibility_score'])
                    st.markdown("<hr>", unsafe_allow_html=True)
                    st.markdown(f"""
                    <div style='border:2px solid #111;padding:20px 28px;font-family:"Space Mono",monospace;background:#f8f8f8'>
                        <span style='font-size:0.7rem;text-transform:uppercase;letter-spacing:1px;color:#888'>SUPERVISOR RECOMMENDATION</span><br>
                        <span style='font-size:1.4rem;font-weight:800;color:#111'>{winner.upper()}</span>
                        <span class='cyan' style='font-size:0.9rem'>&nbsp;— Superior by {margin:.1f} pts</span>
                    </div>
                    """, unsafe_allow_html=True)

    # ════════════════════════════════════════════
    with tab3:
        section_header("SMART REGION SCANNER", "AI-driven hotspot discovery for any city.")
        
        c_scan, c_info = st.columns([1, 1])
        with c_scan:
            st.markdown("<span class='accent-label'>🏙️ Target City Scan</span>", unsafe_allow_html=True)
            scan_city = st.text_input("Enter city for scanner", value="Newark, NJ", placeholder="e.g. Philadelphia, PA", key="scan_city", label_visibility="collapsed")
            
            st.info("💡 **Demo Tip**: High-fidelity GIS zoning active for **NY/NJ/PA**. Try 'Newark' or 'Philadelphia' for real-world land use filtering.")
            
            density = st.select_slider("Scan Density (Grid Size)", options=[4, 6, 8, 10], value=6)
            st.caption(f"Scanner will evaluate {density**2} coordinates within municipal boundaries.")
            
            scan_btn = st.button("EXECUTE REGION SCAN", key="scan_btn")
            
        with c_info:
            st.markdown("""
            <div style='background:#f8f8f8; padding:20px; border:1px solid #ddd'>
                <p style='margin:0; font-size:0.85rem'>
                    The <strong>Smart Scanner</strong> performs a multi-stage discovery:
                    <br><br>
                    1. <strong>Spatial Filtering</strong>: Immediately rejects non-industrial zones using the local GIS database.
                    <br>2. <strong>Grid Analysis</strong>: Parallel scoring of power, connectivity, and risk.
                    <br>3. <strong>Hotspot Ranking</strong>: Identifies top 3 high-feasibility sites.
                </p>
            </div>
            """, unsafe_allow_html=True)

        if scan_btn and scan_city:
            # Show animated radar during scan
            radar_placeholder = st.empty()
            radar_placeholder.markdown(f"""
                <div class="radar-container">
                    <div class="radar-scan-line"></div>
                    <div class="radar-pulse"></div>
                    <div class="radar-pulse" style="animation-delay: 1.5s"></div>
                    <div class="radar-label">📡 SCANNING {scan_city.upper()}...</div>
                </div>
            """, unsafe_allow_html=True)
            
            # Perform actual scan (the pipeline is now async/parallel)
            hotspots = recommend_hotspots(scan_city, grid_size=density, top_n=3)
            
            # Remove radar and show results
            radar_placeholder.empty()
            
            if hotspots:
                st.success(f"Successfully identified {len(hotspots)} hotspots in {scan_city}!")
                
                # Visualize on Map
                map_df = pd.DataFrame([{'lat': h['latitude'], 'lon': h['longitude'], 'name': h['address']} for h in hotspots])
                st.map(map_df, zoom=11)
                
                # Display Rankings
                for i, h in enumerate(hotspots):
                    with st.expander(f"🏆 HOTSPOT #{i+1}: Score {h['total_score']:.1f} — {h['address'][:60]}..."):
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Power Capacity", f"{h['power_capacity_mw']} MW")
                        m2.metric("PUE (Predicted)", f"{h['live_pue']:.2f}")
                        m3.metric("Water Stability", h['water_availability'])
                        
                        st.write(f"**Detailed Zone:** {h['zoning_type']} ({h['permit_status']})")
                        if st.button(f"RUN DEEP ANALYSIS FOR SITE #{i+1}"):
                            st.session_state["lat1"] = h['latitude']
                            st.session_state["lon1"] = h['longitude']
                            st.info("Switching to SINGLE SITE tab for deep analysis...")
                            # Note: Streamlit usually requires a rerun or JS trigger to switch tabs programmatically
            else:
                st.error("No industrial/commercial feasible sites found in this grid density. Try increasing density or picking a different city.")

if __name__ == "__main__":
    main()
