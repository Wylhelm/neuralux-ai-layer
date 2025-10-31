#!/usr/bin/env python3
import duckdb
import argparse
from pathlib import Path

# --- Configuration ---
DB_FILE = Path(__file__).parent.parent / "data/temporal/timeline.duckdb"

def query_timeline(table_name: str, limit: int):
    """Connects to the DuckDB timeline and queries a specific table."""
    if not DB_FILE.exists():
        print(f"Error: Database file not found at {DB_FILE}")
        print("Is the temporal service running? (make start-all)")
        return

    print(f"🔎 Querying timeline database: {DB_FILE}")
    try:
        con = duckdb.connect(database=str(DB_FILE), read_only=True)
        
        if table_name == "all":
            tables = ["command_events", "file_events", "app_focus_events", "system_snapshot_events"]
        else:
            tables = [f"{table_name}_events"]

        for table in tables:
            print(f"\n--- Contents of {table} (last {limit} entries) ---")
            try:
                result = con.execute(f"SELECT * FROM {table} ORDER BY timestamp DESC LIMIT {limit}").fetchdf()
                if not result.empty:
                    print(result.to_string())
                else:
                    print("No events found in this table.")
            except duckdb.CatalogException:
                print(f"Table '{table}' does not exist yet.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if 'con' in locals():
            con.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query the Neuralux Temporal Timeline database.")
    parser.add_argument(
        "table", 
        nargs="?", 
        default="all", 
        choices=["command", "file", "app_focus", "system_snapshot", "all"],
        help="The event table to query. Defaults to 'all'."
    )
    parser.add_argument(
        "--limit", 
        type=int, 
        default=10,
        help="Number of recent events to display."
    )
    args = parser.parse_args()
    
    query_timeline(args.table, args.limit)
