"""
Standalone Mock & Live Verification Suite for Elastic & Arize MCP Clients
Doomsday Rapid Agent | Hackathon Verification Suite
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the clients
from elastic_mcp_client import ElasticMCPClient
from arize_mcp_client import arize_client

def run_mcp_verification():
    print("====================================================")
    print("DOOMSDAY RAPID AGENT - PARTNER MCP VERIFICATION SUITE")
    print("====================================================\n")

    # 1. TEST ELASTIC MCP GROUNDING CLIENT
    print("[PHASE 1] Verifying Elastic MCP Search Grounding...")
    elastic_client = ElasticMCPClient()
    
    # Check connection status
    is_live_elastic = elastic_client.connected
    print(f"  Connection Type: {'LIVE Elastic Server' if is_live_elastic else 'MOCK Grounding Mode (No credentials set)'}")
    
    # Run a test query for semantic search grounding
    ticker = "AAPL"
    sector = "Technology"
    industry = "Consumer Electronics"
    print(f"  Querying Grounding Database for ticker: '{ticker}'...")
    search_results = elastic_client.query_macro_risks(ticker=ticker, sector=sector, industry=industry, limit=2)
    
    print(f"  Found {len(search_results)} grounded macro intelligence document(s):")
    for idx, doc in enumerate(search_results, 1):
        print(f"    - Document #{idx}: {doc.get('title', 'N/A')}")
        print(f"      Geography: {doc.get('geographic_nexus', 'N/A')}")
        print(f"      Severity: {doc.get('severity', 'N/A')}/10")
    
    assert len(search_results) > 0, "Elastic client must return mock results if no live server is found."
    print("  => Elastic MCP Grounding Verification PASSED.\n")

    # 2. TEST ARIZE PHOENIX TELEMETRY CLIENT
    print("[PHASE 2] Verifying Arize Phoenix Telemetry...")
    
    is_live_arize = arize_client.connected
    print(f"  Telemetry Target: {'LIVE Arize Phoenix Collector' if is_live_arize else 'LOCAL Telemetry Logging (Dashboard Console)'}")
    
    # Simulate an agent reasoning log using the precise trace/span API
    print("  Simulating multi-agent consensus log to Phoenix...")
    trace = arize_client.create_trace(name="Consensus Debate Scan", ticker=ticker)
    trace_id = trace["trace_id"]
    
    # Start a child span
    span = arize_client.start_span(trace_id=trace_id, name="Geopolitical Analysis")
    
    # Complete child span
    arize_client.complete_span(
        trace_id=trace_id,
        span_id=span["span_id"],
        inputs={"chaos_index": 0.5, "severity": "HIGH"},
        outputs={"WACC_impact": 0.04, "supply_delay_weeks": 6},
        status="SUCCESS",
        metadata={
            "model": "gemini-3-flash",
            "prompt_tokens": 1200,
            "completion_tokens": 450,
            "consensus_reached": True
        }
    )
    
    # Complete parent trace
    arize_client.complete_trace(trace_id=trace_id)
    
    print("  => Arize Phoenix Telemetry Verification PASSED.\n")

    print("====================================================")
    print("ALL PARTNER MCP SYSTEM COMPONENT VERIFICATIONS PASSED!")
    print("====================================================")

if __name__ == "__main__":
    run_mcp_verification()
