import sys
import os
import pandas as pd

# Add core_engine to path
sys.path.append(os.path.join(os.getcwd(), 'core_engine'))
from scoring_logic import calculate_feasibility_scores

def test_weights():
    # Setup paths
    csv_path = os.path.join(os.getcwd(), 'data_pipeline', 'site_data.csv')
    
    # Define two different weight sets
    weights_energy = {"Energy": 1.0, "Latency": 0.0, "Risk": 0.0, "Tax": 0.0}
    weights_risk = {"Energy": 0.0, "Latency": 0.0, "Risk": 1.0, "Tax": 0.0}
    
    print(f"Testing weights with file: {csv_path}")
    
    # Calculate scores with Energy priority
    df_energy = calculate_feasibility_scores(csv_path, weights_energy)
    score_energy = df_energy.iloc[0]['feasibility_score']
    
    # Calculate scores with Risk priority
    df_risk = calculate_feasibility_scores(csv_path, weights_risk)
    score_risk = df_risk.iloc[0]['feasibility_score']
    
    print(f"Site 0 - Energy Priority Score: {score_energy:.2f}")
    print(f"Site 0 - Risk Priority Score: {score_risk:.2f}")
    
    if score_energy != score_risk:
        print("✅ SUCCESS: Weights are dynamically influencing scores.")
    else:
        print("❌ FAILURE: Weights did not change the score.")

if __name__ == "__main__":
    try:
        test_weights()
    except Exception as e:
        print(f"Error during test: {e}")
