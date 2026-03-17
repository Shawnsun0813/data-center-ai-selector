"""
LLM Interface — Dual-Provider Adapter v3
Supports Google Gemini and OpenAI GPT-4o.

v3 improvements over v2:
  1. Few-Shot examples embedded in each system prompt for stable output format
  2. Per-expert temperature strategy (physics=low, brand=high)
  3. Post-processing: enforces strict 2-sentence output regardless of LLM verbosity
  4. System/User prompt separation (Gemini system_instruction, OpenAI system role)
  5. Structured <site_data> XML tags for clean data injection
"""

import re
from typing import Optional

# ────────────────────────────────────────────────────────────────
# Post-processing: enforce exactly 2 sentences
# ────────────────────────────────────────────────────────────────

def _truncate_to_two_sentences(text: str) -> str:
    """
    Takes potentially verbose LLM output and returns exactly 2 sentences.
    Handles edge cases: single sentence, bullet points, excessive whitespace.
    """
    text = text.strip()
    # Remove markdown bullets, numbered lists, asterisks
    text = re.sub(r'^[\s]*[-*•]\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[\s]*\d+[.)]\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\*+', '', text)   # Remove bold/italic markers
    text = ' '.join(text.split())      # Collapse whitespace
    
    # Split on sentence-ending punctuation followed by space or end
    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if len(sentences) == 0:
        return text
    elif len(sentences) == 1:
        return sentences[0]
    else:
        return f"{sentences[0]} {sentences[1]}"


# ────────────────────────────────────────────────────────────────
# Per-Expert Temperature Map
# ────────────────────────────────────────────────────────────────

EXPERT_TEMPERATURES = {
    "elon":    0.45,   # Precise, technical, low variance
    "buffett": 0.50,   # Measured, consistent value-speak
    "gates":   0.55,   # Data-driven but some nuance allowed
    "jobs":    0.85,   # Poetic, theatrical, high creative variance
}


# ────────────────────────────────────────────────────────────────
# Core call function — system+user separated, post-processed
# ────────────────────────────────────────────────────────────────

def call_llm(
    system_prompt: str,
    user_prompt: str,
    provider: str = "gemini",
    api_key: str = "",
    max_tokens: int = 200,
    temperature: float = 0.6,
    expert_name: str = "",
) -> str:
    """
    Calls the selected LLM with separated system and user prompts.
    Applies per-expert temperature override if expert_name is provided.
    Post-processes output to enforce 2-sentence constraint.
    """
    if not api_key:
        return ""   # Signal to caller to use rule-based fallback

    # Per-expert temperature override
    temp = EXPERT_TEMPERATURES.get(expert_name, temperature)

    try:
        if provider == "gemini":
            raw = _call_gemini(system_prompt, user_prompt, api_key, max_tokens, temp)
        elif provider == "openai":
            raw = _call_openai(system_prompt, user_prompt, api_key, max_tokens, temp)
        else:
            return ""
    except Exception as e:
        return f"[API Error: {e}]"

    # Post-process: enforce 2-sentence output
    return _truncate_to_two_sentences(raw)


def _call_gemini(
    system_prompt: str,
    user_prompt: str,
    api_key: str,
    max_tokens: int,
    temperature: float,
) -> str:
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=system_prompt,
    )
    response = model.generate_content(
        user_prompt,
        generation_config=genai.types.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
        )
    )
    return response.text.strip()


def _call_openai(
    system_prompt: str,
    user_prompt: str,
    api_key: str,
    max_tokens: int,
    temperature: float,
) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system",  "content": system_prompt},
            {"role": "user",    "content": user_prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()


# ────────────────────────────────────────────────────────────────
# Expert Prompts v3 — with Few-Shot examples
# ────────────────────────────────────────────────────────────────

def build_elon_prompts(site: dict) -> tuple[str, str]:
    """Elon Musk — First Principles Physics & Thermal Engineering"""

    system_prompt = """You are Elon Musk evaluating a data center site from first principles.

Your analytical framework:
1. All problems reduce to physics. PUE is a thermodynamic efficiency ratio — heat in vs work out.
2. Cooling is the binding constraint. Only ambient temperature and airflow architecture matter.
3. Never accept "adequate power" as good enough — question the physics.

<example_output>
A PUE of 1.13 at 18°C ambient is near the Carnot limit for free-air cooling — this site runs at the edge of thermodynamic efficiency. Deploy liquid immersion cooling to shave another 0.03 and hit true physics-optimal.
</example_output>

Output rules:
- Exactly 2 sentences. Sentence 1: physics verdict referencing PUE + temp. Sentence 2: one engineering recommendation.
- Tone: direct, technical, zero hedging."""

    user_prompt = f"""<site_data>
  <location>{site.get('address', f"{site.get('latitude', 0)}, {site.get('longitude', 0)}")}</location>
  <ambient_temperature_c>{site.get('ambient_temp_c', 'N/A')}</ambient_temperature_c>
  <predicted_pue>{site.get('predicted_pue', 1.5):.3f}</predicted_pue>
  <power_capacity_mw>{site.get('power_capacity_mw', 0.0):.1f}</power_capacity_mw>
  <grid_stability_pct>{site.get('grid_stability', 0.0)*100:.0f}</grid_stability_pct>
</site_data>

First-principles verdict on this site's thermal and power efficiency?"""

    return system_prompt, user_prompt


def build_buffett_prompts(site: dict) -> tuple[str, str]:
    """Warren Buffett — Value Investing & Economic Moat"""

    system_prompt = """You are Warren Buffett analyzing a capital infrastructure investment.

Your investment framework:
1. Rule #1: Never lose money. Rule #2: Never forget rule #1.
2. Only invest where there is a durable competitive advantage that generates predictable cash flows.
3. Regulatory and permit risk are uncontrollable cost variables that destroy returns.

<example_output>
At $128M ten-year OPEX with verified permits, this site has the kind of cost predictability I look for — the moat is the locked-in energy contract and favorable zoning. The single risk I'd flag is the "Pending" permit status: until that's resolved, you're buying a lottery ticket, not an asset.
</example_output>

Output rules:
- Exactly 2 sentences. Sentence 1: OPEX predictability and moat quality. Sentence 2: single biggest risk.
- Tone: measured Midwestern, Berkshire shareholder letter."""

    user_prompt = f"""<site_data>
  <location>{site.get('address', f"{site.get('latitude', 0)}, {site.get('longitude', 0)}")}</location>
  <opex_10yr_million_usd>{site.get('opex_10yr_m', 0.0):.1f}</opex_10yr_million_usd>
  <margin_of_safety_score>{site.get('pillar_financials', 0.0):.2f}</margin_of_safety_score>
  <permit_status>{site.get('permit_status', 'N/A')}</permit_status>
  <zoning_type>{site.get('zoning_type', 'N/A')}</zoning_type>
  <feasibility_score>{site.get('feasibility_score', 0.0):.1f}</feasibility_score>
</site_data>

Investment verdict — would you hold this asset for 20 years?"""

    return system_prompt, user_prompt


def build_gates_prompts(site: dict) -> tuple[str, str]:
    """Bill Gates — Infrastructure Strategy & Climate Policy"""

    system_prompt = """You are Bill Gates evaluating a data center from an infrastructure and climate policy perspective.

Your evaluation framework:
1. Energy infrastructure is a 30-year bet. Carbon intensity today predicts stranded asset risk tomorrow.
2. Grid proximity determines resilience and future renewable integration capacity.
3. Governments are repricing carbon. High-intensity grids face escalating compliance costs.

<example_output>
At 220 gCO2/kWh and 3.2 km from the nearest substation, this site sits in a nuclear-hydro corridor with strong decarbonization trajectory — excellent for long-term ESG compliance. However, emerging state-level carbon pricing legislation could add $2-4M annually if the grid mix shifts toward gas peakers during peak demand.
</example_output>

Output rules:
- Exactly 2 sentences. Sentence 1: carbon and grid resilience verdict (cite gCO2/kWh). Sentence 2: long-term policy risk.
- Tone: data-driven, policy-literate, Breakthrough Energy white paper."""

    user_prompt = f"""<site_data>
  <location>{site.get('address', f"{site.get('latitude', 0)}, {site.get('longitude', 0)}")}</location>
  <carbon_intensity_gco2_per_kwh>{site.get('carbon_intensity_gco2', 0.0):.0f}</carbon_intensity_gco2_per_kwh>
  <distance_to_substation_km>{site.get('dist_to_substation_km', 0.0):.1f}</distance_to_substation_km>
  <grid_carbon_score>{site.get('pillar_disaster', site.get('carbon_score', 0.0)):.2f}</grid_carbon_score>
  <grid_stability_pct>{site.get('grid_stability', 0.0)*100:.0f}</grid_stability_pct>
</site_data>

Infrastructure and climate resilience verdict?"""

    return system_prompt, user_prompt


def build_jobs_prompts(site: dict) -> tuple[str, str]:
    """Steve Jobs — Brand Narrative & Talent Positioning"""

    system_prompt = """You are Steve Jobs evaluating whether a data center site can be branded as "insanely great."

Your evaluation framework:
1. Details matter. The most important facilities have clean, compelling stories.
2. Talent follows narrative. Great engineers want to work somewhere that feels like the future.
3. Accessibility is not logistics — it is a statement about what kind of company you are.

<example_output>
This site has a clean-energy story that practically writes the press release — 92% renewable, highway-adjacent, and in a region that signals ambition, not compromise. Embed a visitor center with floor-to-ceiling glass overlooking the server hall and you'll turn infrastructure into theater.
</example_output>

Output rules:
- Exactly 2 sentences. Sentence 1: narrative power and brand premium verdict. Sentence 2: one design/positioning recommendation.
- Tone: visionary, precise, slightly theatrical. 2007 Apple Keynote."""

    user_prompt = f"""<site_data>
  <location>{site.get('address', f"{site.get('latitude', 0)}, {site.get('longitude', 0)}")}</location>
  <brand_premium_score>{site.get('pillar_connectivity', 0.0):.2f}</brand_premium_score>
  <feasibility_score>{site.get('feasibility_score', 0.0):.1f}</feasibility_score>
  <distance_to_highway_km>{site.get('dist_to_highway_km', 'N/A')}</distance_to_highway_km>
  <carbon_score>{site.get('pillar_disaster', site.get('carbon_score', 0.0)):.2f}</carbon_score>
</site_data>

Does this site have the story to attract the world's best engineers and partners?"""

    return system_prompt, user_prompt
