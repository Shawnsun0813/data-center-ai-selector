import requests
import pandas as pd
import os
import io
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime

# ==========================================
# Official Public grid endpoints
# ==========================================
NYISO_EXCEL_URL = "https://www.nyiso.com/documents/20142/1407078/NYISO-Interconnection-Queue.xlsx"
PJM_LOCAL_CSV = "cache/pjm_queue_export.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
}

def scrape_pjm_queue() -> pd.DataFrame:
    """
    Reads PJM's Interconnection Queue from a local CSV export.
    PJM has locked down public APIs, so users must export the CSV from PJM Data Miner 
    and place it at cache/pjm_queue_export.csv.
    Sub-selects for PA and NJ projects (Data Center relevant).
    """
    print(f"[pjm_nyiso_scraper] Reading PJM Queue from local file: {PJM_LOCAL_CSV} ...")
    if not os.path.exists(PJM_LOCAL_CSV):
        print(f"[pjm_nyiso_scraper] WARNING: {PJM_LOCAL_CSV} not found. PJM data will be empty. Please download from PJM Data Miner.")
        return pd.DataFrame()
        
    try:
        df = pd.read_csv(PJM_LOCAL_CSV)
        
        # Normalize columns
        df.columns = df.columns.astype(str).str.strip().str.lower()
        
        state_col = "state" if "state" in df.columns else next((c for c in df.columns if "state" in c), None)
        status_col = "status" if "status" in df.columns else next((c for c in df.columns if "status" in c), "project status")
        mw_col = "total_mw" if "total_mw" in df.columns else next((c for c in df.columns if "mw" in c or "capacity" in c), "total capacity (mw)")
        sub_col = "point of interconnection" if "point of interconnection" in df.columns else next((c for c in df.columns if "interconn" in c), None)
        
        if state_col:
            df = df[df[state_col].str.upper().isin(["PA", "NJ"])]
            
        df_clean = pd.DataFrame({
            "iso": "PJM",
            "queue_id": df.get("queue number", df.get("queue", "")),
            "project_name": df.get("project name", df.get("name", "")),
            "state": df.get(state_col, "").astype(str).str.upper(),
            "county": df.get("county", ""),
            "status": df.get(status_col, ""),
            "requested_mw": pd.to_numeric(df.get(mw_col, 0), errors="coerce").fillna(0),
            "substation": df.get("transmission owner", "") + " / " + df.get(sub_col, "").astype(str),
            "latitude": None,
            "longitude": None,
            "last_updated": datetime.now().strftime("%Y-%m-%d")
        })
        
        # Active projects in PJM: Under Study, Engineering, Partially in Service
        active_regex = r"Study|Engineering|Active|Engineering and Procurement|Partially in Service"
        df_active = df_clean[df_clean["status"].astype(str).str.contains(active_regex, case=False, na=False)]
        print(f"[pjm_nyiso_scraper] Found {len(df_active)} active PJM queue projects in PA/NJ.")
        return df_active
    except Exception as e:
        print(f"[pjm_nyiso_scraper] Failed to parse local PJM CSV: {e}")
        return pd.DataFrame()


def scrape_nyiso_queue() -> pd.DataFrame:
    """
    Downloads NYISO's public Interconnection Queue Excel file and parses it.
    """
    print(f"[pjm_nyiso_scraper] Fetching NYISO Queue from {NYISO_EXCEL_URL} ...")
    try:
        res = requests.get(NYISO_EXCEL_URL, headers=HEADERS, timeout=30)
        res.raise_for_status()
        
        df = pd.read_excel(io.BytesIO(res.content), engine="openpyxl")
        df.columns = df.columns.astype(str).str.strip().str.lower()
        
        status_col = "status" if "status" in df.columns else next((c for c in df.columns if "status" in c), None)
        mw_col = "sp q (mw)" if "sp q (mw)" in df.columns else next((c for c in df.columns if "mw" in c), None)
        
        df_clean = pd.DataFrame({
            "iso": "NYISO",
            "queue_id": df.get("queue pos.", df.get("queue", "")),
            "project_name": df.get("project name", ""),
            "state": "NY",
            "county": df.get("county", ""),
            "status": df.get(status_col, ""),
            "requested_mw": pd.to_numeric(df.get(mw_col, 0), errors="coerce").fillna(0),
            "substation": df.get("interconnection point", ""),
            "latitude": None,
            "longitude": None,
            "last_updated": datetime.now().strftime("%Y-%m-%d")
        })
        
        # Drop Withdrawn (W) or In-Service (IS). Keep Active numeric states or purely "Active"
        invalid = ["W", "WITHDRAWN", "IS", "IN-SERVICE", "IN SERVICE"]
        df_active = df_clean[~df_clean["status"].astype(str).str.upper().str.strip().isin(invalid)]
        
        print(f"[pjm_nyiso_scraper] Found {len(df_active)} active NYISO queue projects in NY.")
        return df_active
    except Exception as e:
        print(f"[pjm_nyiso_scraper] Failed to fetch NYISO Excel: {e}")
        return pd.DataFrame()


import sys
from sqlalchemy import create_engine

def get_db_engine():
    """
    Creates an SQLAlchemy engine connected to the Oracle VM PostgreSQL instance via SSH.
    """
    # These should be defined in your .env file
    ssh_host = os.environ.get("SSH_HOST")         # Public IP of the Oracle VM
    ssh_user = os.environ.get("SSH_USER", "ubuntu") # Oracle instances usually use ubuntu or opc
    ssh_pkey = os.environ.get("SSH_PKEY_PATH")    # Path to the private key .pem or .key
    
    db_host = os.environ.get("DB_HOST", "127.0.0.1")
    db_port = int(os.environ.get("DB_PORT", 5432))
    db_name = os.environ.get("DB_NAME", "site_selection")
    db_user = os.environ.get("DB_USER", "postgres")
    db_pass = os.environ.get("DB_PASS", "postgres")
    
    # If no SSH host is provided, attempt direct connection (for local dev/testing)
    if not ssh_host:
        print("[pjm_nyiso_scraper] No SSH_HOST found in env. Attempting direct DB connection.")
        conn_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        return create_engine(conn_url)
        
    print(f"[pjm_nyiso_scraper] establishing SSH tunnel to {ssh_host}...")
    try:
        from sshtunnel import SSHTunnelForwarder
        tunnel = SSHTunnelForwarder(
            (ssh_host, 22),
            ssh_username=ssh_user,
            ssh_pkey=ssh_pkey,
            remote_bind_address=(db_host, db_port)
        )
        tunnel.start()
        
        # Connect SQLAlchemy through the local forwarded port
        conn_url = f"postgresql://{db_user}:{db_pass}@127.0.0.1:{tunnel.local_bind_port}/{db_name}"
        engine = create_engine(conn_url)
        # Attach the tunnel to the engine so we can close it later if needed (hacky but useful)
        engine.ssh_tunnel = tunnel 
        print(f"[pjm_nyiso_scraper] SSH tunnel active on local port {tunnel.local_bind_port}")
        return engine
    except ImportError:
        print("[pjm_nyiso_scraper] ERROR: sshtunnel is not installed.")
        return None
    except Exception as e:
        print(f"[pjm_nyiso_scraper] Failed to start SSH tunnel: {e}")
        return None

def upsert_to_oracle_vm(df: pd.DataFrame, table_name="grid_interconnection_queue"):
    """
    Pushes the active queue dataframe to the PostgreSQL database on the Oracle VM.
    Replaces the table dynamically.
    """
    engine = get_db_engine()
    if not engine:
        print("[pjm_nyiso_scraper] DB Engine unavailable. Caching locally only.")
        return
        
    try:
        print(f"[pjm_nyiso_scraper] Upserting {len(df)} rows to {table_name}...")
        df.to_sql(table_name, engine, if_exists="replace", index=False)
        print(f"[pjm_nyiso_scraper] Successfully upserted to Oracle VM Database.")
    except Exception as e:
        print(f"[pjm_nyiso_scraper] Database upsert failed: {e}")
        print("[pjm_nyiso_scraper] Make sure PostgreSQL is running on the Oracle VM and credentials are correct.")
    finally:
        # Close SSH tunnel if it was opened
        if hasattr(engine, "ssh_tunnel"):
            engine.ssh_tunnel.stop()
            print("[pjm_nyiso_scraper] SSH tunnel closed.")

def run_scraper_and_cache_locally(output_path="cache/grid_queue_active.csv"):
    """
    Runs both scrapers, concatenates the results, and saves to a local CSV cache.
    """
    pjm_df = scrape_pjm_queue()
    nyiso_df = scrape_nyiso_queue()
    
    dfs_to_concat = []
    if not pjm_df.empty: dfs_to_concat.append(pjm_df)
    if not nyiso_df.empty: dfs_to_concat.append(nyiso_df)
        
    if not dfs_to_concat:
        print("[pjm_nyiso_scraper] Both scrapes failed. Returning empty DataFrame.")
        cols = ["iso", "queue_id", "project_name", "state", "county", "status", "requested_mw", "substation", "latitude", "longitude", "last_updated"]
        return pd.DataFrame(columns=cols)

    combined_df = pd.concat(dfs_to_concat, ignore_index=True)
    
    # Save to local cache as a staging mechanism
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    combined_df.to_csv(output_path, index=False)
    print(f"[pjm_nyiso_scraper] Saved {len(combined_df)} total active projects to {output_path}")
    
    return combined_df

if __name__ == "__main__":
    df = run_scraper_and_cache_locally()
    if not df.empty:
        upsert_to_oracle_vm(df)
        print(df.sample(min(5, len(df))))
