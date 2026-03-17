import os
import sys

# Ensure sub-modules can be found when run from root
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, "data_pipeline"))
sys.path.append(os.path.join(current_dir, "core_engine"))

import pandas as pd
from data_pipeline.pipeline_aggregator import run_pipeline

import importlib
import core_engine.scoring_logic
importlib.reload(core_engine.scoring_logic)
from core_engine.scoring_logic import calculate_feasibility_scores

from core_engine.report_generator import generate_report

class DataScoutAgent:
    """
    Agent responsible for data collection and aggregation.
    """
    def collect_data(self, coordinates):
        print("🔍 [DataScoutAgent] Initializing data acquisition for targets...")
        csv_path = run_pipeline(coordinates)
        return csv_path

class ScoringAnalystAgent:
    """
    Agent responsible for quantitative analysis and risk assessment.
    """
    def analyze_sites(self, csv_path, weights, llm_config=None):
        print("⚖️ [ScoringAnalystAgent] Analyzing site feasibility with custom weighting...")
        scored_df = calculate_feasibility_scores(csv_path, weights, llm_config=llm_config)
        return scored_df

class InfraStrategistAgent:
    """
    Agent responsible for long-term grid and policy analysis (Bill Gates).
    """
    def evaluate_strategy(self, scored_df, weights, llm_config=None):
        print("🌍 [InfraStrategistAgent] Assessing sustainability and grid outlook...")
        return scored_df

class DesignArchitectAgent:
    """
    Agent responsible for aesthetic and brand positioning (Steve Jobs).
    """
    def evaluate_design(self, scored_df, weights, llm_config=None):
        print("🎨 [DesignArchitectAgent] Evaluating premium edge positioning...")
        return scored_df

class DecisionSupportAgent:
    """
    Agent responsible for summarizing findings for executive review.
    """
    def generate_briefing(self, scored_df):
        print("📋 [DecisionSupportAgent] Generating unified executive summary...")
        top_candidates = scored_df.sort_values(by='feasibility_score', ascending=False).head(3)
        return top_candidates

    def produce_report(self, site_res, llm_config=None):
        print("📑 [DecisionSupportAgent] Authoring high-fidelity executive briefing...")
        return generate_report(site_res)

    def generate_live_rationales(self, site_row: dict, llm_config: dict) -> dict:
        """
        Calls all 4 specialist LLMs using separated System/User prompts (v3).
        Per-expert temperature, few-shot examples, and 2-sentence enforcement.
        """
        import importlib
        import llm_interface
        importlib.reload(llm_interface)
        from llm_interface import (
            call_llm,
            build_elon_prompts, build_buffett_prompts,
            build_gates_prompts, build_jobs_prompts
        )
        
        provider = llm_config.get("provider", "")
        api_key = llm_config.get("api_key", "")
        
        rationales = {}
        
        def _get_or_fallback(build_fn, expert_name, fallback_text):
            sys_p, usr_p = build_fn(site_row)
            r = call_llm(sys_p, usr_p, provider, api_key, expert_name=expert_name)
            return r if r and not r.startswith("[API") else fallback_text
        
        rationales["elon"] = _get_or_fallback(
            build_elon_prompts, "elon",
            "Elon: Efficient physics profile." if site_row.get('predicted_pue', 1.5) < 1.3
            else "Elon: Thermal inefficiency detected — unacceptable."
        )
        rationales["buffett"] = _get_or_fallback(
            build_buffett_prompts, "buffett",
            "Buffett: Strong OPEX moat with predictable returns." if site_row.get('norm_opex', 0) > 0.7
            else "Buffett: Narrow margin of safety — insufficient."
        )
        rationales["gates"] = _get_or_fallback(
            build_gates_prompts, "gates",
            "Gates: Robust grid outlook, low carbon policy risk." if site_row.get('carbon_score', 0) > 0.6
            else "Gates: Carbon policy risk is a long-term liability."
        )
        rationales["jobs"] = _get_or_fallback(
            build_jobs_prompts, "jobs",
            "Jobs: Premium site — world-class story." if site_row.get('brand_premium_score', 0) > 0.6
            else "Jobs: This site has no soul. Fix it or don't build it."
        )
        
        return rationales

class SiteSelectionSupervisor:
    """
    The Orchestrator that coordinates the expanded specialist panel.
    """
    def __init__(self):
        self.scout = DataScoutAgent()
        self.analyst = ScoringAnalystAgent()
        self.strategist = InfraStrategistAgent()
        self.architect = DesignArchitectAgent()
        self.advisor = DecisionSupportAgent()
        self.state = {
            "current_data_path": None,
            "analysis_results": None,
            "top_sites": None
        }

    def execute_workflow(self, targets, weights=None, llm_config=None):
        print("\n🚀 [Supervisor] Dispatching Global Expert Panel...")
        print("="*60)
        
        # Step 1: Scouting
        self.state["current_data_path"] = self.scout.collect_data(targets)
        
        # Step 2: Quantitative Analysis (Elon / Buffett / etc)
        results = self.analyst.analyze_sites(self.state["current_data_path"], weights, llm_config=llm_config)
        
        # Step 3: Strategic Outlook (Gates)
        results = self.strategist.evaluate_strategy(results, weights, llm_config)
        
        # Step 4: Brand & Design (Jobs)
        results = self.architect.evaluate_design(results, weights, llm_config)
        
        # Step 5: Final Advisor Review
        self.state["analysis_results"] = results
        self.state["top_sites"] = self.advisor.generate_briefing(results)
        
        print("\n🏆 [Supervisor] Workflow Complete. Final Recommendations:")
        print(self.state["top_sites"][['latitude', 'longitude', 'zoning_type', 'feasibility_score']])
        print("="*60)
        
        return self.state["top_sites"]

if __name__ == "__main__":
    # Example execution targets
    test_targets = [
        (38.8048, -77.0469),  # Alexandria, VA
        (40.7128, -74.0060),  # New York, NY
        (39.0438, -77.4874),  # Ashburn, VA (Data Center Alley)
        (34.0522, -118.2437)  # Los Angeles, CA
    ]
    
    supervisor = SiteSelectionSupervisor()
    supervisor.execute_workflow(test_targets)
