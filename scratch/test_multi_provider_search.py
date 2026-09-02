"""
Test script for Multi-Provider Search Fallback Engine
Tests Tavily, Serper, and DuckDuckGo fallback mechanisms.
"""

import os
import sys

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath("."))

from search_providers import (
    search_tavily,
    search_serper,
    search_duckduckgo,
    multi_provider_web_search
)

def test_search_fallback():
    query = "Autonomous AI Agent Orchestration Architectures"
    print("--- 1. Testing Direct Tavily Search ---")
    ok, msg, res = search_tavily(query)
    print(f"Tavily Result: ok={ok}, msg={msg}, items={len(res)}")

    print("\n--- 2. Testing Direct DuckDuckGo Search (Zero-Config Fallback) ---")
    ok_ddg, msg_ddg, res_ddg = search_duckduckgo(query)
    print(f"DuckDuckGo Result: ok={ok_ddg}, msg={msg_ddg}, items={len(res_ddg)}")
    if res_ddg:
        print(f"Sample DDG Title: {res_ddg[0]['title']}")
        print(f"Sample DDG URL: {res_ddg[0]['url']}")

    print("\n--- 3. Testing Orchestrated Multi-Provider Search ---")
    output, provider_used = multi_provider_web_search(query, log_callback=lambda m: print(f"LOG: {m}"))
    print(f"\nFinal Provider Used: {provider_used}")
    print("Output Preview:\n" + output[:400] + "...")

    import time
    print("\n--- 4. Testing Fallback Simulation (Invalidating Tavily API Key) ---")
    time.sleep(1.2)
    original_key = os.environ.get("TAVILY_API_KEY")
    os.environ["TAVILY_API_KEY"] = "invalid_key_for_testing"
    
    output_fb, provider_fb = multi_provider_web_search(query, log_callback=lambda m: print(f"FALLBACK LOG: {m}"))
    print(f"\nFallback Provider Used: {provider_fb}")
    print("Fallback Output Preview:\n" + output_fb[:400] + "...")

    # Restore key
    if original_key:
        os.environ["TAVILY_API_KEY"] = original_key

    print("\n[OK] Multi-Provider Search Fallback Test Complete!")

if __name__ == "__main__":
    test_search_fallback()
