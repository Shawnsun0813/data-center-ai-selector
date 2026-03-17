"""
Data Center Site Selection — Six Pillar Scoring Engine (v3)
===========================================================
Industry-grade weighted scoring model based on research from:
- AWS / Google / Microsoft hyperscaler methodology
- JLL / CBRE / Cushman & Wakefield broker frameworks
- Uptime Institute Tier Assessment standards

Six Pillars:
1. Power & Energy (35%)     — Capacity, cost, stability, carbon
2. Connectivity & Fiber (18%) — Fiber, substation, latency
3. Natural Disaster Risk (15%) — FEMA NRI, safety score
4. Water & Cooling (12%)    — Water access, PUE, ambient temperature
5. Land & Zoning (10%)      — Zoning type, permit status
6. Financials & Incentives (10%) — Energy cost, OpEx projection
"""

import pandas as pd
import numpy as np
import os

# ─── Default Pillar Weights ─────────────────────────────────────────────
DEFAULT_WEIGHTS = {
    "Power":        0.35,
    "Connectivity": 0.18,
    "Disaster":     0.15,
    "Water":        0.12,
    "Land":         0.10,
    "Financials":   0.10,
}

# ─── Lookup Tables ──────────────────────────────────────────────────────
ZONING_SCORES = {
    'Industrial': 1.0,
    'Industrial-Light': 0.85,
    'Commercial': 0.70,
    'Office': 0.55,
    'Agricultural': 0.30,
    'Residential': 0.05,
}

PERMIT_SCORES = {
    'Verified': 1.0,
    'In-Progress': 0.6,
    'Pending Review': 0.4,
    'Pre-approval Required': 0.3,
    'Restricted': 0.0,
}

# Major US data center hubs (lat, lon) for latency proxy
DC_HUBS = [
    (39.0438, -77.4874),   # Ashburn, VA  (Data Center Alley)
    (40.7128, -74.0060),   # New York, NY (Financial Hub)
    (41.8781, -87.6298),   # Chicago, IL  (Midwest Hub)
    (32.7767, -96.7970),   # Dallas, TX   (South Central)
    (45.5152, -122.6784),  # Portland, OR (Pacific NW)
]


def _safe_minmax(series: pd.Series, invert: bool = False) -> pd.Series:
    """Min-max normalize a series to [0, 1]. If invert=True, lower raw = higher score."""
    s_min, s_max = series.min(), series.max()
    if s_max - s_min < 1e-9:
        return pd.Series(1.0, index=series.index)
    normed = (series - s_min) / (s_max - s_min)
    return (1.0 - normed) if invert else normed


def _col_or_fallback(df: pd.DataFrame, primary: str, fallback_val) -> pd.Series:
    """Return column if it exists, otherwise a constant Series."""
    if primary in df.columns:
        return df[primary].fillna(fallback_val)
    return pd.Series(fallback_val, index=df.index)


def _min_hub_distance(lat: float, lon: float) -> float:
    """Approximate minimum distance (km) to nearest major DC hub."""
    dists = [
        np.sqrt((lat - h[0])**2 + (lon - h[1])**2) * 111
        for h in DC_HUBS
    ]
    return min(dists)


# ═══════════════════════════════════════════════════════════════════════
# CORE FUNCTION
# ═══════════════════════════════════════════════════════════════════════
def calculate_feasibility_scores(csv_path: str, weights: dict = None, llm_config: dict = None) -> pd.DataFrame:
    """
    Reads site data CSV and calculates a feasibility score (0-100)
    across six industry-standard pillars.

    Args:
        csv_path:  Path to the pipeline-generated site_data.csv
        weights:   Optional dict overriding pillar weights (must sum to 1.0)

    Returns:
        DataFrame sorted by feasibility_score (descending), with pillar
        breakdowns and executive rationale per site.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    # Normalize weights so they always sum to 1.0 (prevents scores > 100 if UI omits some pillars)
    total_w = sum(w.values())
    if total_w > 0:
        w = {k: v / total_w for k, v in w.items()}

    # ── PILLAR 1: Power & Energy (35%) ─────────────────────────────────
    norm_capacity = _safe_minmax(df['power_capacity_mw'])
    grid_stab     = _col_or_fallback(df, 'grid_stability', 0.80)
    carbon_raw    = _col_or_fallback(df, 'carbon_intensity_gco2', 400)
    carbon_score  = (1.0 - carbon_raw / 800).clip(0, 1)
    price_raw     = _col_or_fallback(df, 'retail_price_cents_kwh', 11.0)
    price_score   = _safe_minmax(price_raw, invert=True)

    df['pillar_power'] = (
        norm_capacity * 0.30 +
        grid_stab     * 0.25 +
        price_score   * 0.25 +
        carbon_score  * 0.20
    )

    # ── PILLAR 2: Connectivity & Fiber (18%) ───────────────────────────
    fiber_km   = _col_or_fallback(df, 'dist_to_fiber_km', 10.0)
    fiber_sc   = (1.0 - fiber_km / 30).clip(0, 1)
    sub_km     = _col_or_fallback(df, 'dist_to_substation_km', 15.0)
    sub_sc     = (1.0 - sub_km / 25).clip(0, 1)
    df['dist_to_hub_km'] = df.apply(
        lambda r: _min_hub_distance(r['latitude'], r['longitude']), axis=1
    )
    latency_sc = (1.0 - df['dist_to_hub_km'] / 4000).clip(0, 1)

    df['pillar_connectivity'] = (
        fiber_sc   * 0.40 +
        sub_sc     * 0.25 +
        latency_sc * 0.35
    )

    # ── PILLAR 3: Natural Disaster Risk (15%) ──────────────────────────
    # FEMA NRI risk_score: higher = more risk. safety_score: higher = safer.
    safety   = _col_or_fallback(df, 'safety_score', 0.5)
    fema_raw = _col_or_fallback(df, 'fema_risk_score', 50.0)
    fema_sc  = _safe_minmax(fema_raw, invert=True)   # lower risk = better

    df['pillar_disaster'] = (
        safety  * 0.50 +
        fema_sc * 0.50
    )

    # ── PILLAR 4: Water & Cooling (12%) ────────────────────────────────
    water_sc    = _col_or_fallback(df, 'water_score', 0.5)
    pue_raw     = _col_or_fallback(df, 'live_pue', 1.3)
    pue_sc      = ((1.5 - pue_raw) / 0.4).clip(0, 1)   # Target PUE 1.1
    temp_raw    = _col_or_fallback(df, 'ambient_temp_c', 18.0)
    temp_sc     = _safe_minmax(temp_raw, invert=True)   # cooler = better

    df['pillar_water'] = (
        water_sc * 0.35 +
        pue_sc   * 0.35 +
        temp_sc  * 0.30
    )

    # ── PILLAR 5: Land & Zoning (10%) ──────────────────────────────────
    zoning_sc = df['zoning_type'].map(ZONING_SCORES).fillna(0.1)
    permit_sc = df['permit_status'].map(PERMIT_SCORES).fillna(0.0)

    df['pillar_land'] = (
        zoning_sc * 0.55 +
        permit_sc * 0.45
    )

    # ── PILLAR 6: Financials & Incentives (10%) ────────────────────────
    # OpEx 10yr projection (lower is better)
    # 1 MW = 1000 kW. 1 year = 8760 hrs.
    # Cost per yr = MW * 1000 * 8760 * (cents/100) = MW * cents * 87,600 = $M * 0.0876
    # 10-year cost ($M) = MW * cents * 0.876
    df['opex_10yr_m'] = df['power_capacity_mw'] * price_raw * 0.876
    opex_sc = _safe_minmax(df['opex_10yr_m'], invert=True)
    # Land cost proxy (inversely correlated with hub distance — hub = expensive)
    land_cost_sc = _safe_minmax(df['dist_to_hub_km'])   # farther = cheaper

    df['pillar_financials'] = (
        opex_sc      * 0.60 +
        land_cost_sc * 0.40
    )

    # ── FINAL FEASIBILITY SCORE ────────────────────────────────────────
    df['feasibility_score'] = (
        df['pillar_power']        * w['Power'] +
        df['pillar_connectivity'] * w['Connectivity'] +
        df['pillar_disaster']     * w['Disaster'] +
        df['pillar_water']        * w['Water'] +
        df['pillar_land']         * w['Land'] +
        df['pillar_financials']   * w['Financials']
    ) * 100

    # ── PUE for display ────────────────────────────────────────────────
    df['predicted_pue'] = pue_raw

    # ── EXECUTIVE RATIONALE ────────────────────────────────────────────
    def _rationale(row):
        parts = []
        # Power verdict
        if row['pillar_power'] > 0.7:
            parts.append("⚡ Strong grid: high capacity, competitive pricing")
        elif row['pillar_power'] > 0.4:
            parts.append("⚡ Adequate grid, moderate cost pressure")
        else:
            parts.append("⚡ Power constraint: limited capacity or high cost")

        # Connectivity verdict
        if row['pillar_connectivity'] > 0.7:
            parts.append("🌐 Tier-1 connectivity hub")
        else:
            parts.append("🌐 Secondary connectivity profile")

        # Disaster verdict
        if row['pillar_disaster'] > 0.7:
            parts.append("🛡️ Low natural hazard exposure")
        elif row['pillar_disaster'] > 0.4:
            parts.append("🛡️ Moderate risk — mitigation required")
        else:
            parts.append("🛡️ HIGH RISK: significant disaster exposure")

        # Water/Cooling verdict
        if row['pillar_water'] > 0.7:
            parts.append("💧 Excellent cooling conditions")
        elif row['pillar_water'] > 0.4:
            parts.append("💧 Adequate water/cooling")
        else:
            parts.append("💧 Water scarcity or thermal stress")

        # Zoning verdict
        if row['pillar_land'] > 0.6:
            parts.append("📋 Permit-ready site")
        else:
            parts.append("📋 Zoning/permit hurdles expected")

        return " | ".join(parts)

    df['rationale'] = df.apply(_rationale, axis=1)

    # ── OUTPUT COLUMNS ─────────────────────────────────────────────────
    display_cols = [
        'latitude', 'longitude',
        'power_capacity_mw', 'grid_stability', 'carbon_intensity_gco2',
        'predicted_pue', 'opex_10yr_m',
        'zoning_type', 'permit_status',
        'pillar_power', 'pillar_connectivity', 'pillar_disaster',
        'pillar_water', 'pillar_land', 'pillar_financials',
        'feasibility_score', 'rationale',
    ]
    # Only keep columns that actually exist
    out_cols = [c for c in display_cols if c in df.columns]
    return df[out_cols].sort_values(by='feasibility_score', ascending=False)


# ═══════════════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(current_dir, "..", "data_pipeline", "site_data.csv")

    try:
        results = calculate_feasibility_scores(data_path)
        print("🏆 Six Pillar Site Selection Analysis:")
        print("=" * 80)
        for _, row in results.iterrows():
            print(f"\n📍 ({row['latitude']}, {row['longitude']}) — Score: {row['feasibility_score']:.1f}/100")
            print(f"   Power: {row.get('pillar_power', 0):.2f} | "
                  f"Connect: {row.get('pillar_connectivity', 0):.2f} | "
                  f"Disaster: {row.get('pillar_disaster', 0):.2f} | "
                  f"Water: {row.get('pillar_water', 0):.2f} | "
                  f"Land: {row.get('pillar_land', 0):.2f} | "
                  f"Finance: {row.get('pillar_financials', 0):.2f}")
            print(f"   {row['rationale']}")

        output_file = os.path.join(current_dir, "scored_sites.csv")
        results.to_csv(output_file, index=False)
        print(f"\n📊 Results saved to: {output_file}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
