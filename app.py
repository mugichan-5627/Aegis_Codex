"""
DOOMSDAY RAPID AGENT - Institutional Financial Intelligence Engine
Version: 3.1 (Stabilized - Progressive Rendering)
ASCII-Clean | Timeout-Protected | Stream-First Architecture
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import json
import os
import math
import time
import signal
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from dotenv import load_dotenv
import requests
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import threading

# ===============================================================
# RAPID AGENT MCP & TELEMETRY INTEGRATIONS
# ===============================================================
from elastic_mcp_client import ElasticMCPClient
from arize_mcp_client import arize_client


# ===============================================================
# ROBUST ENV LOADER — ALWAYS loads from absolute path first
# This permanently fixes the CWD-dependent key-not-found error
# ===============================================================
import pathlib

_env_path = pathlib.Path(__file__).resolve().parent / ".env"

# Search fallback paths if not found next to this file
if not _env_path.exists():
    for _p in [
        pathlib.Path.cwd() / ".env",
        pathlib.Path.cwd().parent / ".env",
        pathlib.Path(__file__).parent.parent / ".env",
    ]:
        if _p.exists():
            _env_path = _p
            break

_env_exists = _env_path.exists()

# Step 1: Try python-dotenv with the absolute path (override=True forces re-read)
if _env_exists:
    load_dotenv(dotenv_path=_env_path, override=True)

# Step 2: Manual line-by-line parser as bulletproof fallback
# Runs always when file exists — ensures no key is ever missed
if _env_exists:
    try:
        with open(_env_path, encoding='utf-8', errors='ignore') as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith('#') and '=' in _line:
                    _k, _v = _line.split('=', 1)
                    _k = _k.strip()
                    _v = _v.strip().strip('"').strip("'")
                    if _k and _v and not os.environ.get(_k):  # Don't overwrite existing
                        os.environ[_k] = _v
    except:
        pass

def apply_user_keys():
    """Override env keys with user-provided sidebar keys if present."""
    llm_key = st.session_state.get('user_llm_key', '').strip()
    tavily_key = st.session_state.get('user_tavily_key', '').strip()
    phoenix_key = st.session_state.get('user_phoenix_key', '').strip()
    phoenix_endpoint = st.session_state.get('user_phoenix_endpoint', '').strip()
    
    if llm_key:
        if llm_key.startswith("AIzaSy"):
            os.environ["GOOGLE_API_KEY"] = llm_key
        elif llm_key.startswith("nvapi-"):
            os.environ["NVIDIA_API_KEY"] = llm_key
        elif llm_key.startswith("fw_"):
            os.environ["FIREWORKS_API_KEY"] = llm_key
        else:
            # Default: try as Google key (most common for hackathon participants)
            os.environ["GOOGLE_API_KEY"] = llm_key
    
    if tavily_key:
        os.environ["TAVILY_API_KEY"] = tavily_key

    if phoenix_key:
        os.environ["PHOENIX_API_KEY"] = phoenix_key
        os.environ["ARIZE_API_KEY"] = phoenix_key
        
    if phoenix_endpoint:
        os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = phoenix_endpoint
        os.environ["PHOENIX_COLLECTOR_URL"] = phoenix_endpoint
        
    # Re-initialize Arize telemetry client if keys are provided dynamically
    if phoenix_key or phoenix_endpoint:
        try:
            from arize_mcp_client import arize_client
            arize_client.initialize_collector()
        except Exception:
            pass

# ===============================================================
# PAGE CONFIG
# ===============================================================

st.set_page_config(
    page_title="DOOMSDAY RAPID AGENT",
    page_icon="[+]",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===============================================================
# DATA MODELS
# ===============================================================

@dataclass
class WorldState:
    timestamp: str = ""
    vix: float = 20.0
    vix_trend: str = "stable"
    dxy: float = 104.0
    us_10y_yield: float = 4.5
    oil_brent: float = 80.0
    gold: float = 2400.0
    fear_level: str = "CAUTIOUS"
    active_crises: List[Dict] = field(default_factory=list)

@dataclass
class FractureNode:
    node_id: str
    risk_id: str
    latitude: float
    longitude: float
    label: str
    description: str
    category: str
    severity: float
    probability: float
    threat_level: str
    affected_assets: List[str] = field(default_factory=list)
    time_horizon: str = "6_months"
    revenue_at_risk_pct: float = 5.0

@dataclass
class DebateMessage:
    role: str
    content: str
    round_number: int
    confidence: float = 0.5

@dataclass
class RiskVerdict:
    risk_id: str
    risk_description: str
    domain: str
    severity_score: float
    probability: float
    time_horizon: str
    bull_summary: str
    bear_summary: str
    judge_reasoning: str
    geographic_nexus: str
    revenue_at_risk_pct: float
    debate_transcript: List[DebateMessage] = field(default_factory=list)
    grounding_citation: Optional[str] = None


@dataclass
class SimpleValuation:
    current_price: float = 0.0
    base_fair_value: float = 0.0
    distressed_value: float = 0.0
    downside_pct: float = 0.0
    valuation_method: str = "Multi-Factor DCF"
    base_wacc: float = 10.0
    stressed_wacc: float = 15.0
    revenue_haircut: float = 0.0
    margin_compression_bps: float = 0.0
    waterfall_data: List[Dict] = field(default_factory=list)
    method_values: Dict = field(default_factory=dict)

@dataclass 
class CompanyData:
    ticker: str = ""
    name: str = ""
    sector: str = "Unknown"
    industry: str = "Unknown"
    market_cap: float = 0.0
    revenue: float = 0.0
    ebitda: float = 0.0
    net_income: float = 0.0
    total_debt: float = 0.0
    cash: float = 0.0
    shares_outstanding: float = 1.0
    current_price: float = 0.0
    revenue_growth: float = 0.0
    beta: float = 1.0
    pe_ratio: float = 0.0
    company_type: str = "mature"
    city: str = ""
    country: str = ""



# ===============================================================
# CSS - Complete Dark Monitor Theme (ASCII-Clean)
# ===============================================================

THEME_CSS = """
<style>
    /* Immersive Dark Mode - Remove white top bar while keeping toggle arrow accessible */
    header, [data-testid="stHeader"], div[data-testid="stHeader"] {
        background-color: transparent !important;
        background: transparent !important;
        border-bottom: none !important;
        box-shadow: none !important;
        pointer-events: none;
    }
    
    /* Ensure the collapsed sidebar toggle arrow remains clickable and styled beautifully */
    div[data-testid="collapsedControl"] {
        pointer-events: auto !important;
        background-color: #0c1018 !important;
        border: 1px solid #1a2538 !important;
        border-radius: 4px !important;
        padding: 4px !important;
        margin: 10px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    
    div[data-testid="collapsedControl"] * {
        color: #00ffd0 !important;
    }
    
    .stApp {
        background-color: #080b10;
        color: #c8d6e5;
    }
    section[data-testid="stSidebar"] {
        background-color: #0c1018;
        border-right: 1px solid #1a2538;
    }
    
    .header-bar {
        background: linear-gradient(135deg, #0c1018 0%, #14080a 50%, #0c1018 100%);
        border: 1px solid #2a1520;
        border-radius: 6px;
        padding: 12px 24px;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .header-title {
        font-family: 'JetBrains Mono', 'Courier New', monospace;
        font-size: 1.2em;
        color: #ff3344;
        letter-spacing: 4px;
        text-transform: uppercase;
        text-shadow: 0 0 12px rgba(255, 51, 68, 0.4);
    }
    .header-meta {
        font-family: monospace;
        font-size: 0.7em;
        color: #5a6f82;
    }
    .status-badge {
        display: inline-block;
        font-family: monospace;
        font-size: 0.65em;
        padding: 3px 8px;
        border-radius: 8px;
        border: 1px solid;
        margin-left: 8px;
    }
    .badge-active { border-color: #00e676; color: #00e676; background: rgba(0,230,118,0.08); }
    .badge-threat { border-color: #ff6d00; color: #ff6d00; background: rgba(255,109,0,0.08); animation: pulse 2s infinite; }
    .badge-critical { border-color: #ff1744; color: #ff1744; background: rgba(255,23,68,0.08); animation: pulse 1.5s infinite; }
    
    @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.6; } }
    
    .metrics-grid {
        display: grid;
        grid-template-columns: repeat(6, 1fr);
        gap: 10px;
        margin-bottom: 20px;
    }
    .m-card {
        background: #0c1018;
        border: 1px solid #1a2538;
        border-radius: 6px;
        padding: 14px 10px;
        text-align: center;
        transition: border-color 0.3s;
    }
    .m-card:hover { border-color: #2a4058; }
    .m-val {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.4em;
        font-weight: 700;
        color: #eceff1;
    }
    .m-label {
        font-size: 0.6em;
        color: #5a6f82;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-top: 4px;
    }
    
    .c-red { color: #ff1744 !important; }
    .c-orange { color: #ff6d00 !important; }
    .c-yellow { color: #ffd600 !important; }
    .c-green { color: #00e676 !important; }
    .c-blue { color: #448aff !important; }
    .c-critical { color: #ff1744 !important; animation: pulse 1.5s infinite; }
    
    .section-hdr {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.78em;
        color: #5a6f82;
        letter-spacing: 2.5px;
        text-transform: uppercase;
        margin: 14px 0 6px 0;
        padding-bottom: 4px;
        border-bottom: 1px solid #1a2538;
    }
    
    /* Tighter sidebar layout */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
        gap: 0.4rem !important;
    }
    
    .terminal-feed {
        background: #0a0e14;
        border: 1px solid #1a2538;
        border-radius: 6px;
        padding: 12px 16px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72em;
        line-height: 1.8;
        max-height: 400px;
        overflow-y: auto;
    }
    .t-line { 
        margin: 2px 0; 
        font-weight: bold !important;
    }
    .t-time { color: #5a6f82 !important; }
    .t-ok { color: #00e676 !important; font-weight: bold !important; }
    .t-warn { color: #ff6d00 !important; font-weight: bold !important; }
    .t-err { color: #ff1744 !important; font-weight: bold !important; }
    .t-info { color: #448aff !important; font-weight: bold !important; }
    .t-dim { color: #8a9ba8 !important; font-weight: bold !important; opacity: 0.8; }
    
    .risk-card {
        background: #0c1018;
        border: 1px solid #1a2538;
        border-radius: 6px;
        padding: 14px;
        margin-bottom: 10px;
        border-left: 3px solid;
        transition: border-color 0.3s, background 0.3s;
    }
    .risk-card:hover { background: #0e1420; }
    .risk-critical { border-left-color: #ff1744; }
    .risk-high { border-left-color: #ff6d00; }
    .risk-elevated { border-left-color: #ffd600; }
    .risk-monitoring { border-left-color: #00e676; }
    
    .risk-title {
        font-size: 0.85em;
        font-weight: 600;
        color: #eceff1;
        margin-bottom: 6px;
    }
    .risk-meta {
        font-size: 0.7em;
        color: #5a6f82;
        display: flex;
        gap: 15px;
        margin-bottom: 8px;
    }
    .risk-desc {
        font-size: 0.78em;
        color: #8a9ba8;
        line-height: 1.5;
    }
    
    .debate-msg {
        margin: 8px 0;
        padding: 10px 14px;
        border-radius: 6px;
        font-size: 0.78em;
        line-height: 1.5;
        border-left: 3px solid;
    }
    .msg-bear { background: rgba(255,23,68,0.05); border-left-color: #ff1744; }
    .msg-bull { background: rgba(0,230,118,0.05); border-left-color: #00e676; }
    .msg-judge { background: rgba(255,214,0,0.05); border-left-color: #ffd600; }
    .msg-role {
        font-weight: 700;
        font-size: 0.68em;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 4px;
        opacity: 0.7;
    }
    
    .info-panel {
        background: #0c1018;
        border: 1px solid #1a2538;
        border-radius: 6px;
        padding: 14px;
    }
    .ws-row {
        display: flex;
        justify-content: space-between;
        padding: 5px 0;
        border-bottom: 1px solid #0f1520;
        font-size: 0.8em;
    }
    .ws-k { color: #5a6f82; }
    .ws-v { color: #eceff1; font-family: monospace; }
    
    .landing-box {
        text-align: center;
        padding: 80px 40px;
    }
    .landing-title {
        font-family: 'JetBrains Mono', monospace;
        font-size: 2.2em;
        color: #ff3344;
        letter-spacing: 6px;
        text-shadow: 0 0 20px rgba(255,51,68,0.3);
        margin-bottom: 16px;
    }
    .landing-sub {
        font-size: 0.88em;
        color: #5a6f82;
        max-width: 650px;
        margin: 0 auto;
        line-height: 1.7;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    ::-webkit-scrollbar { width: 5px; }
    ::-webkit-scrollbar-track { background: #080b10; }
    ::-webkit-scrollbar-thumb { background: #1a2538; border-radius: 3px; }
    
    div[data-testid="stExpander"] {
        border: 1px solid #1a2538;
        border-radius: 6px;
        background: #0a0e14;
    }
    
    /* Keep expander header permanently dark with bright high-contrast text and no white flashes */
    div[data-testid="stExpander"] [data-testid="stExpanderHeader"],
    div[data-testid="stExpander"] button,
    div[data-testid="stExpander"] summary,
    div[data-testid="stExpander"] [data-testid="stExpanderHeader"]:hover,
    div[data-testid="stExpander"] button:hover,
    div[data-testid="stExpander"] [data-testid="stExpanderHeader"]:focus,
    div[data-testid="stExpander"] button:focus,
    div[data-testid="stExpander"] [data-testid="stExpanderHeader"]:active,
    div[data-testid="stExpander"] button:active {
        background-color: #0c1018 !important;
        color: #eceff1 !important;
        border: none !important;
        box-shadow: none !important;
        outline: none !important;
    }
    
    /* Ensure all nested text inside the expander header stays perfectly bright and high-contrast */
    div[data-testid="stExpander"] [data-testid="stExpanderHeader"] *,
    div[data-testid="stExpander"] button *,
    div[data-testid="stExpander"] summary * {
        color: #eceff1 !important;
    }
    
    /* Highlight open/hovered expander titles slightly with our beautiful neon cyan */
    div[data-testid="stExpander"] [data-testid="stExpanderHeader"]:hover *,
    div[data-testid="stExpander"] button:hover * {
        color: #00ffd0 !important;
    }

    /* === Dynamic Telemetry Visualizer Animations === */
    .telemetry-container {
        background: #0a0e14;
        border: 1px solid #1a2538;
        border-radius: 6px;
        padding: 16px;
        margin-top: 15px;
        margin-bottom: 15px;
    }
    .telemetry-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #162030;
        padding-bottom: 10px;
        margin-bottom: 15px;
    }
    .telemetry-title {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8em;
        font-weight: 700;
        color: #00ffd0;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .telemetry-status-pulse {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #00ffd0;
        box-shadow: 0 0 8px #00ffd0;
        animation: telemetryPulse 1.5s infinite alternate;
    }
    @keyframes telemetryPulse {
        0% { opacity: 0.3; transform: scale(0.8); }
        100% { opacity: 1; transform: scale(1.2); }
    }
    .telemetry-node-swarm {
        animation: swarmPulse 2s infinite alternate;
    }
    @keyframes swarmPulse {
        0% { r: 13; filter: drop-shadow(0 0 2px rgba(255, 51, 68, 0.4)); }
        100% { r: 16; filter: drop-shadow(0 0 10px rgba(255, 51, 68, 0.8)); }
    }
    .telemetry-node-arize {
        animation: arizePulse 2s infinite alternate;
    }
    @keyframes arizePulse {
        0% { r: 13; filter: drop-shadow(0 0 2px rgba(0, 255, 208, 0.4)); }
        100% { r: 16; filter: drop-shadow(0 0 10px rgba(0, 255, 208, 0.8)); }
    }
    .telemetry-dash-pipe {
        stroke-dasharray: 6, 6;
        animation: dashFlow 25s linear infinite;
    }
    @keyframes dashFlow {
        to {
            stroke-dashoffset: -1000;
        }
    }
    
    /* Super-strong brute force selector for all sidebar labels, widget texts, and expander inputs */
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] label p,
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] label,
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] *,
    [data-testid="stSidebar"] div[data-testid="stExpander"] label,
    [data-testid="stSidebar"] div[data-testid="stExpander"] label p,
    [data-testid="stSidebar"] div[data-testid="stExpander"] p,
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] div,
    [data-testid="stSidebar"] p {
        color: #ffffff !important;
        font-weight: 600 !important;
        opacity: 0.95 !important;
        text-shadow: 0 0 1px rgba(255, 255, 255, 0.1) !important;
        -webkit-text-fill-color: #ffffff !important;
    }
</style>
"""

st.markdown(THEME_CSS, unsafe_allow_html=True)


# ===============================================================
# TIMEOUT UTILITY
# ===============================================================

def run_with_timeout(func, args=(), kwargs=None, timeout=30, default=None):
    """Run a function with a timeout. Returns default if it times out."""
    if kwargs is None:
        kwargs = {}
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(func, *args, **kwargs)
    try:
        res = future.result(timeout=timeout)
        executor.shutdown(wait=False)
        return res
    except (FuturesTimeoutError, Exception) as e:
        executor.shutdown(wait=False)
        return default


# ===============================================================
# AI CLIENT (Simplified, Timeout-Protected)
# ===============================================================

class DoomsdayAI:
    """Single unified AI client with automatic failover and timeouts."""
    
    def __init__(self):
        self.gemini_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.nvidia_key = os.getenv("NVIDIA_API_KEY")
        self.fireworks_key = os.getenv("FIREWORKS_API_KEY")
        self.model = None
        self.provider = None
        self._genai = None
        
    def initialize(self) -> str:
        """Find working model. Returns model name or raises."""
        errors = []
        
        # Try Gemini
        if self.gemini_key:
            try:
                from google import genai
                self._genai = genai.Client(api_key=self.gemini_key)
                result = run_with_timeout(
                    self._test_gemini, timeout=12, default=None
                )
                if result:
                    self.model = result
                    self.provider = "gemini"
                    return f"Gemini [{result}]"
                else:
                    errors.append("Gemini: timeout or invalid key")
            except Exception as e:
                errors.append(f"Gemini: {str(e)[:80]}")
        else:
            errors.append("Gemini: no key (GOOGLE_API_KEY / GEMINI_API_KEY not set)")
        
        # Try NVIDIA — iterate through available models
        if self.nvidia_key:
            nvidia_models = [
                "meta/llama-3.3-70b-instruct",
                "meta/llama-3.1-8b-instruct",
                "meta/llama-3.1-70b-instruct",
                "nvidia/llama-3.1-nemotron-70b-instruct",
                "mistralai/mistral-7b-instruct-v0.3",
            ]
            for model in nvidia_models:
                try:
                    result = run_with_timeout(
                        self._test_openai,
                        args=(model, self.nvidia_key, "https://integrate.api.nvidia.com/v1"),
                        timeout=15, default=None
                    )
                    if result:
                        self.model = model
                        self.provider = "nvidia"
                        return f"NVIDIA [{model.split('/')[-1]}]"
                except Exception as e:
                    errors.append(f"NVIDIA/{model.split('/')[-1]}: {str(e)[:80]}")
                    continue
            errors.append("NVIDIA: all models failed")
        else:
            errors.append("NVIDIA: no key (NVIDIA_API_KEY not set)")
        
        # Try Fireworks
        if self.fireworks_key:
            fw_models = [
                "accounts/fireworks/models/llama-v3p3-70b-instruct",
                "accounts/fireworks/models/llama-v3p1-70b-instruct",
                "accounts/fireworks/models/llama-v3-70b-instruct",
                "accounts/fireworks/models/mixtral-8x7b-instruct",
            ]
            for model in fw_models:
                try:
                    result = run_with_timeout(
                        self._test_openai,
                        args=(model, self.fireworks_key, "https://api.fireworks.ai/inference/v1"),
                        timeout=12, default=None
                    )
                    if result:
                        self.model = model
                        self.provider = "fireworks"
                        return f"Fireworks [{model.split('/')[-1]}]"
                except Exception as e:
                    errors.append(f"Fireworks/{model.split('/')[-1]}: {str(e)[:80]}")
                    continue
            errors.append("Fireworks: all models failed")
        else:
            errors.append("Fireworks: no key (FIREWORKS_API_KEY not set)")
        
        raise ValueError("No AI provider available. Diagnostics: " + " | ".join(errors))
    
    def _test_gemini(self):
        """Test Gemini models."""
        from google.genai import types
        for m in ["gemini-2.0-flash", "gemini-1.5-flash"]:
            try:
                r = self._genai.models.generate_content(
                    model=m, contents="Say OK",
                    config=types.GenerateContentConfig(max_output_tokens=5, temperature=0)
                )
                if r and r.text:
                    return m
            except:
                continue
        return None
    
    def _test_openai(self, model, api_key, base_url):
        """Test OpenAI-compatible endpoint."""
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url)
        r = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Say OK"}],
            max_tokens=5, temperature=0
        )
        if r.choices[0].message.content:
            return True
        return None
    
    def generate(self, prompt: str, temperature: float = 0.4, max_tokens: int = 2048, json_mode: bool = False) -> Optional[str]:
        """Generate text with a strict timeout shield. Returns None on failure."""
        def _gen():
            if self.provider == "gemini":
                return self._gen_gemini(prompt, temperature, max_tokens, json_mode)
            else:
                return self._gen_openai(prompt, temperature, max_tokens, json_mode)
        return run_with_timeout(_gen, timeout=25, default=None)
    
    def _gen_gemini(self, prompt, temp, max_tokens, json_mode):
        from google.genai import types
        config_kwargs = {"temperature": temp, "max_output_tokens": max_tokens}
        if json_mode:
            config_kwargs["response_mime_type"] = "application/json"
        config = types.GenerateContentConfig(**config_kwargs)
        r = self._genai.models.generate_content(model=self.model, contents=prompt, config=config)
        return r.text if r else None
    
    def _gen_openai(self, prompt, temp, max_tokens, json_mode):
        from openai import OpenAI
        if self.provider == "nvidia":
            client = OpenAI(api_key=self.nvidia_key, base_url="https://integrate.api.nvidia.com/v1", timeout=20.0)
        else:
            client = OpenAI(api_key=self.fireworks_key, base_url="https://api.fireworks.ai/inference/v1", timeout=20.0)
        
        kwargs = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temp,
            "max_tokens": max_tokens,
            "timeout": 20.0
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        
        r = client.chat.completions.create(**kwargs)
        return r.choices[0].message.content


def parse_json_safe(text: str) -> Optional[Dict]:
    """Safely parse JSON from LLM output, handling markdown blocks."""
    if not text:
        return None
    text = text.strip()
    # Strip markdown code blocks
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines (``` markers)
        lines = lines[1:] if lines[0].startswith("```") else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
        if text.startswith("json"):
            text = text[4:].strip()
    try:
        return json.loads(text)
    except:
        # Try to find JSON in the text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except:
                pass
    return None


# ===============================================================
# DATA LAYER
# ===============================================================

def resolve_ticker(user_input: str) -> str:
    """
    Smart ticker resolution with dynamic Yahoo Finance search:
    - If already has standard suffix (.NS, .BO, .L, etc.), use as-is.
    - If matches a high-precision synonym, return immediately.
    - If matches a known Indian NSE symbol, append .NS.
    - Otherwise, query Yahoo Finance API to resolve query/name to ticker.
    - Fallback to original input upper-cased.
    """
    ticker = user_input.strip().upper()
    if not ticker:
        return ticker
        
    # Already has a suffix — use as-is
    if "." in ticker:
        return ticker

    # 1. High-precision synonyms / common names
    SYNONYMS = {
        "TSMC": "TSM",
        "GOOGLE": "GOOG",
        "APPLE": "AAPL",
        "MICROSOFT": "MSFT",
        "TESLA": "TSLA",
        "NVIDIA": "NVDA",
        "AMAZON": "AMZN",
        "META": "META",
        "FACEBOOK": "META",
        "NETFLIX": "NFLX",
        "TATA MOTORS": "TATAMOTORS.NS",
        "TATAMOTORS": "TATAMOTORS.NS",
        "TATA": "TATAMOTORS.NS",
        "RELIANCE": "RELIANCE.NS",
        "TCS": "TCS.NS",
        "INFOSYS": "INFY.NS",
        "INFY": "INFY.NS",
        "WIPRO": "WIPRO.NS",
        "HDFC": "HDFCBANK.NS",
        "ICICI": "ICICIBANK.NS",
        "L&T": "LT.NS",
        "TATA STEEL": "TATASTEEL.NS",
        "MARUTI SUZUKI": "MARUTI.NS",
        "ASIAN PAINTS": "ASIANPAINT.NS",
        "BAJAJ FINANCE": "BAJFINANCE.NS",
        "MAHINDRA": "M&M.NS",
        "M&M": "M&M.NS",
        "SBI": "SBIN.NS",
        "STATE BANK OF INDIA": "SBIN.NS",
    }
    
    if ticker in SYNONYMS:
        return SYNONYMS[ticker]
    
    # Known Indian tickers (NSE symbols without suffix)
    INDIAN_TICKERS = {
        "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "HINDUNILVR",
        "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK", "LT", "HCLTECH",
        "AXISBANK", "WIPRO", "ASIANPAINT", "MARUTI", "TITAN", "SUNPHARMA",
        "BAJFINANCE", "BAJFINSV", "NESTLEIND", "ULTRACEMCO", "ONGC",
        "NTPC", "POWERGRID", "TATAMOTORS", "TATASTEEL", "JSWSTEEL",
        "ADANIENT", "ADANIPORTS", "TECHM", "INDUSINDBK", "CIPLA",
        "DRREDDY", "DIVISLAB", "GRASIM", "BRITANNIA", "HINDALCO",
        "EICHERMOT", "HEROMOTOCO", "BAJAJ-AUTO", "TATACONSUM",
        "APOLLOHOSP", "COALINDIA", "BPCL", "UPL", "ZOMATO", "PAYTM",
        "NYKAA", "DMART", "IRCTC", "HAL", "BEL", "VEDL", "M&M",
        "NIFTY50", "SENSEX", "BANKBARODA", "PNB", "CANBK", "UNIONBANK",
        "PIDILITIND", "BERGEPAINT", "HAVELLS", "VOLTAS", "BLUEDART",
        "TORNTPHARM", "ALKEM", "LUPIN", "BIOCON", "AUROPHARMA",
        "TRENT", "VARUN", "JUBLFOOD", "DOMINOS", "METROPOLIS",
    }
    
    if ticker in INDIAN_TICKERS:
        return f"{ticker}.NS"
        
    # Dynamically search Yahoo Finance search API
    try:
        import requests
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={requests.utils.quote(user_input)}&quotesCount=8"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        res = requests.get(url, headers=headers, timeout=4)
        if res.status_code == 200:
            data = res.json()
            quotes = data.get("quotes", [])
            if quotes:
                # Rate and rank to prefer EQUITY on primary US/Indian markets
                def rate_quote(q):
                    sym = q.get("symbol", "").upper()
                    exch = q.get("exchange", "").upper()
                    qtype = q.get("quoteType", "").upper()
                    
                    score = 0
                    if qtype == "EQUITY":
                        score += 10
                    # Major US/Indian exchanges get massive boosts
                    if exch in ["NYQ", "NMS", "NGM", "NCM", "ASE"]:
                        score += 20
                    elif exch in ["NSE", "BSE"]:
                        score += 15
                    # Suffix matches for Indian market
                    if sym.endswith(".NS") or sym.endswith(".BO"):
                        score += 10
                    # Penalize BDRs and weird local exchanges if we can find US/Indian ones
                    if sym.endswith(".SA") or sym.endswith(".BA") or sym.endswith(".MX"):
                        score -= 10
                    return score

                quotes.sort(key=rate_quote, reverse=True)
                best_quote = quotes[0]
                symbol = best_quote.get("symbol")
                if symbol:
                    return symbol.upper()
    except Exception:
        pass
    
    return ticker


def fetch_company_data(ticker: str) -> Optional[CompanyData]:
    """Fetch company data from yfinance with smart ticker resolution and USD conversion."""
    
    def _fetch():
        import yfinance as yf
        import time
        
        # Resolve ticker (handles Indian auto-suffix)
        resolved = resolve_ticker(ticker)
        
        def _get_info(stock_obj):
            """Internal helper to get info with retries and fallback."""
            # Attempt 1: Standard info
            try:
                inf = stock_obj.info
                if inf and inf.get("marketCap", 0) > 0:
                    return inf
            except Exception as e:
                pass
            
            # Attempt 2: Wait and retry info
            time.sleep(1.5)
            try:
                inf = stock_obj.info
                if inf and inf.get("marketCap", 0) > 0:
                    return inf
            except:
                pass
                
            # Attempt 3: Fallback to fast_info for critical metrics
            try:
                fi = stock_obj.fast_info
                if fi and fi.get("marketCap", 0) > 0:
                    return {
                        "marketCap": fi.get("marketCap"),
                        "currentPrice": fi.get("lastPrice"),
                        "regularMarketPrice": fi.get("lastPrice"),
                        "sharesOutstanding": fi.get("shares"),
                        "currency": fi.get("currency", "USD"),
                        "sector": "Unknown (FastInfo Fallback)",
                        "industry": "Unknown (FastInfo Fallback)",
                        "longName": resolved,
                        "quoteType": fi.get("quoteType", "EQUITY")
                    }
            except:
                pass
            return {}

        # Try resolved ticker first
        stock = yf.Ticker(resolved)
        info = _get_info(stock)
        
        # If failed and no suffix, try .NS (Indian NSE)
        if (not info or info.get("marketCap", 0) == 0) and "." not in ticker:
            resolved = f"{ticker.upper()}.NS"
            stock = yf.Ticker(resolved)
            info = _get_info(stock)
        
        # If still failed and was .NS, try .BO (Bombay SE)
        if (not info or info.get("marketCap", 0) == 0) and resolved.endswith(".NS"):
            resolved = resolved.replace(".NS", ".BO")
            stock = yf.Ticker(resolved)
            info = _get_info(stock)
        
        if not info or info.get("marketCap", 0) == 0:
            return None
        
        # === CURRENCY CONVERSION TO USD ===
        currency = info.get("currency", "USD")
        usd_rate = 1.0  # Units of local currency per 1 USD
        
        if currency != "USD":
            try:
                FALLBACK_RATES = {
                    "INR": 83.5, "EUR": 0.92, "GBP": 0.79,
                    "JPY": 155.0, "TWD": 32.5, "KRW": 1380.0,
                    "HKD": 7.82, "SGD": 1.35, "AUD": 1.52, "CAD": 1.37
                }
                if currency == "INR":
                    fx = yf.Ticker("USDINR=X").history(period="1d")
                    usd_rate = float(fx['Close'].iloc[-1]) if not fx.empty else FALLBACK_RATES["INR"]
                elif currency == "EUR":
                    fx = yf.Ticker("EURUSD=X").history(period="1d")
                    usd_rate = 1.0 / float(fx['Close'].iloc[-1]) if not fx.empty else FALLBACK_RATES["EUR"]
                elif currency == "GBP":
                    fx = yf.Ticker("GBPUSD=X").history(period="1d")
                    usd_rate = 1.0 / float(fx['Close'].iloc[-1]) if not fx.empty else FALLBACK_RATES["GBP"]
                elif currency == "JPY":
                    fx = yf.Ticker("USDJPY=X").history(period="1d")
                    usd_rate = float(fx['Close'].iloc[-1]) if not fx.empty else FALLBACK_RATES["JPY"]
                else:
                    fx = yf.Ticker(f"USD{currency}=X").history(period="1d")
                    usd_rate = float(fx['Close'].iloc[-1]) if not fx.empty else FALLBACK_RATES.get(currency, 1.0)
            except Exception:
                FALLBACK_RATES = {
                    "INR": 83.5, "EUR": 0.92, "GBP": 0.79,
                    "JPY": 155.0, "TWD": 32.5, "KRW": 1380.0
                }
                usd_rate = FALLBACK_RATES.get(currency, 1.0)
        
        def to_usd(value):
            """Convert local currency value to USD."""
            if value is None or value == 0:
                return 0.0
            if currency == "USD":
                return float(value)
            return float(value) / usd_rate
        
        # Build CompanyData — everything in USD
        return CompanyData(
            ticker=resolved,
            name=info.get("longName", info.get("shortName", ticker)),
            sector=info.get("sector", "Unknown"),
            industry=info.get("industry", "Unknown"),
            market_cap=to_usd(info.get("marketCap", 0)),
            revenue=to_usd(info.get("totalRevenue", 0) or 0),
            ebitda=to_usd(info.get("ebitda", 0) or 0),
            net_income=to_usd(info.get("netIncomeToCommon", 0) or 0),
            total_debt=to_usd(info.get("totalDebt", 0) or 0),
            cash=to_usd(info.get("totalCash", 0) or 0),
            shares_outstanding=float(info.get("sharesOutstanding", 1) or 1),
            current_price=to_usd(info.get("currentPrice", info.get("regularMarketPrice", 0)) or 0),
            revenue_growth=float(info.get("revenueGrowth", 0) or 0),
            beta=float(info.get("beta", 1.0) or 1.0),
            pe_ratio=float(info.get("trailingPE", 0) or 0),
            city=info.get("city", ""),
            country=info.get("country", ""),
        )

    
    return run_with_timeout(_fetch, timeout=30, default=None)


def fetch_world_state_data() -> WorldState:
    """Fetch market indicators with timeout."""
    ws = WorldState(timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))
    
    def _fetch_indicator(ticker_sym):
        import yfinance as yf
        try:
            data = yf.Ticker(ticker_sym).history(period="2d")
            if not data.empty:
                return round(float(data['Close'].iloc[-1]), 2)
        except:
            pass
        return None
    
    indicators = {"vix": "^VIX", "dxy": "DX-Y.NYB", "us_10y_yield": "^TNX", "oil_brent": "BZ=F", "gold": "GC=F"}
    
    for key, sym in indicators.items():
        val = run_with_timeout(_fetch_indicator, args=(sym,), timeout=8, default=None)
        if val is not None:
            setattr(ws, key, val)
    
    # Calculate fear level
    score = 0
    if ws.vix >= 35: score += 3
    elif ws.vix >= 25: score += 2
    elif ws.vix >= 18: score += 1
    if ws.gold > 2500: score += 1
    if ws.oil_brent > 95: score += 1
    if ws.us_10y_yield > 5.0: score += 1
    ws.fear_level = "PANIC" if score >= 5 else "ANXIOUS" if score >= 3 else "CAUTIOUS" if score >= 2 else "CALM"
    
    return ws


def get_tavily():
    """Get Tavily client."""
    try:
        from tavily import TavilyClient
        key = os.getenv("TAVILY_API_KEY")
        if key:
            return TavilyClient(api_key=key)
    except:
        pass
    return None


def tavily_search(client, query: str, max_results: int = 3) -> str:
    """Safe Tavily search with timeout."""
    if not client:
        return ""
    def _search():
        try:
            result = client.search(query=query, search_depth="advanced", max_results=max_results)
            texts = []
            for r in result.get("results", []):
                texts.append(f"[{r.get('title', '')}]: {r.get('content', '')[:250]}")
            return "\n".join(texts)
        except:
            return ""
    return run_with_timeout(_search, timeout=12, default="") or ""


# ===============================================================
# INTELLIGENCE ENGINE
# ===============================================================

def run_intelligence_scan(ai: "DoomsdayAI", tavily, ticker: str, company: "CompanyData", ws: "WorldState"):
    """Gather intelligence - grounded in Elastic MCP."""
    try:
        from agent_swarm import AgentBuilderSwarm
        swarm = AgentBuilderSwarm(ai)
        return swarm.run_grounded_intelligence_scan(ticker, company, ws, tavily)
    except Exception as e:
        # Robust failover
        return generate_fallback_risks(company, ws)



def generate_fallback_risks(company: "CompanyData", ws: "WorldState"):
    """Generate intelligent fallback risks when AI/search fails."""
    sector = (company.sector or "").lower()
    industry = (company.industry or "").lower()
    name = company.name
    risks = []
    risks.append({
        "id": "RISK_001", "domain": "market",
        "title": f"Global macro deterioration impacting {company.sector}",
        "description": f"With VIX at {ws.vix} and oil at ${ws.oil_brent}, macroeconomic headwinds could compress {name}'s multiples by 15-25%. Rising rates increase discount rates and could trigger multiple compression across the {company.sector} sector.",
        "severity": 5 + (1 if ws.vix > 20 else 0) + (1 if ws.vix > 30 else 0),
        "probability": 0.4, "geographic_nexus": "New York",
        "revenue_at_risk_pct": 8.0, "time_horizon": "6_months"
    })
    if "tech" in sector or "semiconductor" in industry:
        risks.extend([
            {"id": "RISK_002", "domain": "geopolitical",
             "title": "US-China tech export controls escalation",
             "description": f"Escalating US-China tensions could lead to expanded export controls, restricting {name}'s access to Chinese customers. China represents significant semiconductor demand, and further restrictions could reduce revenue by 10-20%.",
             "severity": 7, "probability": 0.45, "geographic_nexus": "Beijing",
             "revenue_at_risk_pct": 15.0, "time_horizon": "6_months"},
            {"id": "RISK_003", "domain": "supply_chain",
             "title": "Taiwan Strait geopolitical risk to manufacturing",
             "description": f"Military escalation in the Taiwan Strait could disrupt semiconductor manufacturing. Even a limited blockade would halt chip production and shipments globally, catastrophically impacting {name}'s operations.",
             "severity": 9, "probability": 0.15, "geographic_nexus": "Taiwan",
             "revenue_at_risk_pct": 40.0, "time_horizon": "12_months"},
            {"id": "RISK_004", "domain": "technology",
             "title": "Competitive disruption from new entrants",
             "description": f"Rapid advances by competitors in AI chips, custom silicon (Google TPU, Amazon Graviton), and emerging architectures could erode {name}'s market share. Technology cycles are accelerating.",
             "severity": 6, "probability": 0.35, "geographic_nexus": "Silicon Valley",
             "revenue_at_risk_pct": 12.0, "time_horizon": "12_months"},
            {"id": "RISK_005", "domain": "regulatory",
             "title": "Antitrust and regulatory scrutiny intensification",
             "description": f"Global regulators are increasingly scrutinizing dominant tech companies. {name} faces potential antitrust investigations in the US, EU, and China that could result in fines or forced licensing.",
             "severity": 5, "probability": 0.3, "geographic_nexus": "Brussels",
             "revenue_at_risk_pct": 8.0, "time_horizon": "12_months"},
        ])
    elif "financial" in sector or "bank" in industry:
        risks.extend([
            {"id": "RISK_002", "domain": "financial",
             "title": "Credit quality deterioration in loan portfolio",
             "description": f"Rising interest rates and economic slowdown could increase non-performing assets. {name}'s loan book may face 50-100bps increase in NPAs, requiring significant provisioning.",
             "severity": 7, "probability": 0.4, "geographic_nexus": "Mumbai" if ".NS" in (company.ticker or "") else "New York",
             "revenue_at_risk_pct": 15.0, "time_horizon": "6_months"},
            {"id": "RISK_003", "domain": "regulatory",
             "title": "Basel IV tighter capital requirements",
             "description": f"New regulatory capital requirements could force {name} to hold additional buffers, reducing return on equity by 100-200bps and limiting dividend capacity.",
             "severity": 5, "probability": 0.5, "geographic_nexus": "Washington DC",
             "revenue_at_risk_pct": 8.0, "time_horizon": "12_months"},
            {"id": "RISK_004", "domain": "market",
             "title": "Net interest margin compression from rate cuts",
             "description": f"If rate cuts begin, {name}'s net interest margin could compress 20-40bps, directly impacting the core earnings driver.",
             "severity": 6, "probability": 0.45, "geographic_nexus": "Washington DC",
             "revenue_at_risk_pct": 12.0, "time_horizon": "6_months"},
            {"id": "RISK_005", "domain": "technology",
             "title": "Fintech disruption of core banking services",
             "description": f"Digital-first challengers and embedded finance are eroding {name}'s retail banking franchise. Neo-banks and DeFi pose medium-term structural threats.",
             "severity": 5, "probability": 0.3, "geographic_nexus": "San Francisco",
             "revenue_at_risk_pct": 10.0, "time_horizon": "12_months"},
        ])
    elif "energy" in sector or "oil" in industry:
        risks.extend([
            {"id": "RISK_002", "domain": "market",
             "title": "Oil price collapse below breakeven",
             "description": f"OPEC+ disagreements or demand destruction could push oil below $60/bbl. This would force {name} to cut capex and potentially suspend dividends.",
             "severity": 7, "probability": 0.3, "geographic_nexus": "Riyadh",
             "revenue_at_risk_pct": 25.0, "time_horizon": "6_months"},
            {"id": "RISK_003", "domain": "regulatory",
             "title": "Accelerated energy transition regulation",
             "description": f"Carbon taxes and renewable mandates could strand {name}'s fossil fuel assets and increase operating costs by 10-15%.",
             "severity": 6, "probability": 0.4, "geographic_nexus": "Brussels",
             "revenue_at_risk_pct": 12.0, "time_horizon": "12_months"},
            {"id": "RISK_004", "domain": "geopolitical",
             "title": "Middle East conflict disrupting supply routes",
             "description": f"Escalation in the Middle East could disrupt shipping through the Strait of Hormuz, affecting 20% of global oil transit and causing operational disruptions for {name}.",
             "severity": 8, "probability": 0.25, "geographic_nexus": "Strait of Hormuz",
             "revenue_at_risk_pct": 18.0, "time_horizon": "3_months"},
            {"id": "RISK_005", "domain": "financial",
             "title": "Stranded asset writedowns",
             "description": f"As the world transitions to renewables, {name} may face impairment charges on exploration assets that become economically unviable.",
             "severity": 5, "probability": 0.35, "geographic_nexus": "Global",
             "revenue_at_risk_pct": 10.0, "time_horizon": "12_months"},
        ])
    else:
        risks.extend([
            {"id": "RISK_002", "domain": "supply_chain",
             "title": f"Supply chain disruption for {company.sector}",
             "description": f"{name} faces potential supply chain disruptions from geopolitical tensions or logistics bottlenecks that could impact production and delivery timelines.",
             "severity": 6, "probability": 0.35, "geographic_nexus": "Shanghai",
             "revenue_at_risk_pct": 12.0, "time_horizon": "6_months"},
            {"id": "RISK_003", "domain": "regulatory",
             "title": "Regulatory environment tightening",
             "description": f"New regulations in {name}'s key markets could increase compliance costs and restrict certain business activities, impacting margins by 200-400 basis points.",
             "severity": 5, "probability": 0.4, "geographic_nexus": "Washington DC",
             "revenue_at_risk_pct": 8.0, "time_horizon": "12_months"},
            {"id": "RISK_004", "domain": "technology",
             "title": "Technology disruption from AI and automation",
             "description": f"AI and automation could disrupt {name}'s business model or enable competitors to undercut on cost. Companies slow to adopt may lose 10-15% market share.",
             "severity": 6, "probability": 0.3, "geographic_nexus": "Silicon Valley",
             "revenue_at_risk_pct": 10.0, "time_horizon": "12_months"},
            {"id": "RISK_005", "domain": "financial",
             "title": "Customer concentration and demand weakness",
             "description": f"Economic slowdown could reduce demand from {name}'s key customers. If top 5 customers cut orders by 15-20%, revenue impact would be material.",
             "severity": 6, "probability": 0.35, "geographic_nexus": "Global",
             "revenue_at_risk_pct": 12.0, "time_horizon": "6_months"},
        ])
    if ".NS" in (company.ticker or "") or ".BO" in (company.ticker or ""):
        risks.append({
            "id": f"RISK_{len(risks)+1:03d}", "domain": "financial",
            "title": "INR depreciation and FX volatility",
            "description": f"Rupee weakness against USD could increase import costs and foreign debt servicing for {name}. A 5-10% INR depreciation would directly compress margins for import-dependent operations.",
            "severity": 5, "probability": 0.4, "geographic_nexus": "Mumbai",
            "revenue_at_risk_pct": 6.0, "time_horizon": "6_months"
        })
    elif "TSM" in (company.ticker or ""):
        risks.append({
            "id": f"RISK_{len(risks)+1:03d}", "domain": "financial",
            "title": "TWD/USD currency headwinds",
            "description": f"Taiwan Dollar appreciation or volatility against USD impacts {name}'s dollar-denominated revenue reporting and could compress reported margins by 200-300bps.",
            "severity": 4, "probability": 0.35, "geographic_nexus": "Taipei",
            "revenue_at_risk_pct": 5.0, "time_horizon": "6_months"
        })
    return risks[:6]


def run_debate(ai: "DoomsdayAI", ticker: str, company: "CompanyData", risk: dict, ws: "WorldState"):
    """Run Bear/Bull/Judge debate with Arize Phoenix telemetry tracing."""
    try:
        from agent_swarm import AgentBuilderSwarm
        swarm = AgentBuilderSwarm(ai)
        verdict = swarm.run_adversarial_tribunal(ticker, company, risk, ws)
        if verdict is not None:
            return verdict
    except Exception as e:
        pass

    # Robust local failover fallback
    risk_desc = risk.get("description", risk.get("title", ""))
    risk_title = risk.get("title", "")
    bear = {"argument": f"This risk poses material downside. {risk_desc} Historical precedents suggest 15-25% drawdown potential in affected segments.", "severity_estimate": risk.get("severity", 6), "confidence": 0.6}
    bull = {"argument": f"The market has largely priced in this risk. {ticker}'s diversified revenue base and strong cash position provide resilience.", "confidence": 0.5}
    judge = {
        "verdict": "VALIDATED" if risk.get("severity", 5) >= 5 else "MONITORING",
        "final_severity": risk.get("severity", 5),
        "final_probability": risk.get("probability", 0.4),
        "reasoning": f"Risk validated based on available evidence. Severity maintained at {risk.get('severity', 5)}/10."
    }
    
    transcript = [
        DebateMessage(role="bear", content=bear["argument"], round_number=1, confidence=0.6),
        DebateMessage(role="bull", content=bull["argument"], round_number=1, confidence=0.5),
        DebateMessage(role="judge", content=judge["reasoning"], round_number=1, confidence=0.9),
    ]
    return RiskVerdict(
        risk_id=risk.get("id", f"RISK_{hash(risk_title) % 999:03d}"),
        risk_description=risk_desc,
        domain=risk.get("domain", "unknown"),
        severity_score=float(judge["final_severity"]),
        probability=float(judge["final_probability"]),
        time_horizon=risk.get("time_horizon", "6_months"),
        bull_summary=bull["argument"],
        bear_summary=bear["argument"],
        judge_reasoning=judge["reasoning"],
        geographic_nexus=risk.get("geographic_nexus", "Global"),
        revenue_at_risk_pct=float(risk.get("revenue_at_risk_pct", 10)),
        debate_transcript=transcript
    )



GLOBAL_COORDS = {
    # --- Asia ---
    "taiwan": (23.69, 120.96), "china": (35.86, 104.19), "beijing": (39.90, 116.40),
    "shanghai": (31.23, 121.47), "shenzhen": (22.54, 114.05), "hong kong": (22.31, 114.17),
    "hsinchu": (24.81, 120.96), "taipei": (25.03, 121.56),
    "india": (20.59, 78.96), "mumbai": (19.07, 72.87), "bangalore": (12.97, 77.59),
    "delhi": (28.61, 77.20), "hyderabad": (17.38, 78.48), "chennai": (13.08, 80.27),
    "japan": (35.67, 139.65), "tokyo": (35.67, 139.65), "osaka": (34.69, 135.50),
    "south korea": (37.56, 126.97), "seoul": (37.56, 126.97), "korea": (37.56, 126.97),
    "singapore": (1.35, 103.81), "vietnam": (14.05, 108.27), "philippines": (12.87, 121.77),
    "asia": (34.0, 100.0), "southeast asia": (10.0, 110.0),
    
    # --- Americas ---
    "usa": (37.09, -95.71), "united states": (37.09, -95.71), "america": (37.09, -95.71),
    "washington": (38.90, -77.04), "new york": (40.71, -74.00),
    "silicon valley": (37.38, -122.05), "san francisco": (37.77, -122.42),
    "mountain view": (37.42, -122.08), "cupertino": (37.32, -122.03),
    "palo alto": (37.44, -122.14), "santa clara": (37.35, -121.95),
    "seattle": (47.60, -122.33), "redmond": (47.67, -122.12), "austin": (30.26, -97.74),
    "california": (36.77, -119.41), "texas": (31.96, -99.90), "florida": (27.66, -81.51),
    "canada": (56.13, -106.34), "brazil": (-14.23, -51.92), "mexico": (23.63, -102.55),
    "north america": (45.0, -100.0), "south america": (-15.0, -60.0),

    # --- Europe ---
    "germany": (51.16, 10.45), "europe": (48.85, 2.35), "london": (51.50, -0.12),
    "paris": (48.85, 2.35), "berlin": (52.52, 13.40), "amsterdam": (52.36, 4.90),
    "brussels": (50.85, 4.35), "switzerland": (46.81, 8.22), "ukraine": (50.45, 30.52),
    "russia": (55.75, 37.61), "moscow": (55.75, 37.61),
    "uk": (55.37, -3.43), "united kingdom": (55.37, -3.43),

    # --- MEA & Others ---
    "middle east": (25.20, 55.27), "dubai": (25.20, 55.27), "israel": (31.77, 35.22),
    "tel aviv": (32.08, 34.78), "strait of hormuz": (26.57, 56.25), "red sea": (20.0, 38.0),
    "australia": (-25.27, 133.77), "sydney": (-33.86, 151.20),
    "global": (20.0, 0.0), "worldwide": (20.0, 0.0),
    "taiwan strait": (24.50, 119.50), "south china sea": (15.0, 115.0),
    "africa": (1.0, 20.0),
}


def resolve_location_coords(location_name: str) -> Optional[Tuple[float, float]]:
    """Query OpenStreetMap Nominatim API with caching & safety guards."""
    if not location_name:
        return None
    loc_clean = location_name.lower().strip()
    
    # 1. Check local/memory cache in GLOBAL_COORDS
    if loc_clean in GLOBAL_COORDS:
        return GLOBAL_COORDS[loc_clean]
    
    # 2. Try Nominatim lookup with User-Agent header (required by OSM terms of service)
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": location_name,
            "format": "json",
            "limit": 1
        }
        headers = {
            "User-Agent": "DoomsdayRapidAgent/1.0 (moosa@users.noreply.github.com)"
        }
        response = requests.get(url, params=params, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                # Cache the result to prevent future hits
                GLOBAL_COORDS[loc_clean] = (lat, lon)
                return (lat, lon)
    except Exception as e:
        # Silently fail and fallback
        pass
    
    return None


def map_risks_to_coords(verdicts: List[RiskVerdict]) -> List[FractureNode]:
    """Map risks to coordinates using shared global database."""
    
    def find_coords(text: str) -> Tuple[float, float]:
        text_lower = text.lower().strip()
        
        # 1. Direct key match
        for key, coords in GLOBAL_COORDS.items():
            if key in text_lower:
                return coords
        
        # 2. Dynamic OSM Nominatim Resolver for full label
        dynamic_coords = resolve_location_coords(text)
        if dynamic_coords:
            return dynamic_coords
            
        # 3. Fallback to Multi-region splitting (e.g. "USA, Asia")
        parts = [p.strip() for p in text_lower.replace(",", " ").replace("/", " ").split()]
        for p in parts:
            if p in GLOBAL_COORDS:
                return GLOBAL_COORDS[p]
            # Try dynamic lookup for each part as well if it's a longer geographic word
            if len(p) > 3:
                p_coords = resolve_location_coords(p)
                if p_coords:
                    return p_coords
        
        # 4. HQ Fallback (Anchor unknown nodes near HQ)
        if "hq" in st.session_state and st.session_state.hq:
            hq_lat, hq_lon, _ = st.session_state.hq
            return (hq_lat + np.random.uniform(-4, 4), hq_lon + np.random.uniform(-4, 4))
            
        return (25.0 + np.random.uniform(-5, 5), -35.0 + np.random.uniform(-10, 10)) # Neutral Atlantic
    
    nodes = []
    for i, v in enumerate(verdicts):
        lat, lon = find_coords(v.geographic_nexus)
        # Add slight jitter
        lat += np.random.uniform(-0.3, 0.3)
        lon += np.random.uniform(-0.3, 0.3)
        
        threat = "critical" if v.severity_score >= 8 else "high" if v.severity_score >= 6 else "elevated" if v.severity_score >= 4 else "monitoring"
        
        nodes.append(FractureNode(
            node_id=f"NODE_{i:03d}",
            risk_id=v.risk_id,
            latitude=lat, longitude=lon,
            label=v.geographic_nexus,
            description=v.risk_description[:120],
            category=v.domain,
            severity=v.severity_score,
            probability=v.probability,
            threat_level=threat,
            revenue_at_risk_pct=v.revenue_at_risk_pct
        ))
    
    return nodes


def get_hq_coords(ticker: str, name: str, city: str = "", country: str = "") -> Tuple[float, float, str]:
    """Known HQ coordinates - US + India + Global with dynamic resolution."""
    c_city = (city or "").lower().strip()
    c_country = (country or "").lower().strip()
    
    # 1. Try high-fidelity dynamic resolution with OpenStreetMap Nominatim
    if city and country:
        full_query = f"{city}, {country}"
        dyn_coords = resolve_location_coords(full_query)
        if dyn_coords:
            lat = dyn_coords[0] + np.random.uniform(-0.02, 0.02)
            lon = dyn_coords[1] + np.random.uniform(-0.02, 0.02)
            return (lat, lon, f"{city}, {country}")
    if city:
        dyn_coords = resolve_location_coords(city)
        if dyn_coords:
            lat = dyn_coords[0] + np.random.uniform(-0.02, 0.02)
            lon = dyn_coords[1] + np.random.uniform(-0.02, 0.02)
            return (lat, lon, f"{city}, {country or 'Global'}")
    if country:
        dyn_coords = resolve_location_coords(country)
        if dyn_coords:
            lat = dyn_coords[0] + np.random.uniform(-0.05, 0.05)
            lon = dyn_coords[1] + np.random.uniform(-0.05, 0.05)
            return (lat, lon, f"{city or 'HQ'}, {country}")

    # 2. First try dynamic resolution using scraped city and country from yfinance against static local keys
    if c_city:
        for k, coords in GLOBAL_COORDS.items():
            if k == c_city or k in c_city:
                # Add slight random jitter
                lat = coords[0] + np.random.uniform(-0.02, 0.02)
                lon = coords[1] + np.random.uniform(-0.02, 0.02)
                return (lat, lon, f"{city}, {country or 'Global'}")
                
    if c_country:
        for k, coords in GLOBAL_COORDS.items():
            if k == c_country or k in c_country:
                lat = coords[0] + np.random.uniform(-0.05, 0.05)
                lon = coords[1] + np.random.uniform(-0.05, 0.05)
                return (lat, lon, f"{city or 'HQ'}, {country}")
                
    # 2. Hardcoded DB lookup for key tickers
    HQ_DB = {
        # === US TECH ===
        "NVDA": (37.37, -121.96, "Santa Clara, CA"),
        "AAPL": (37.33, -122.01, "Cupertino, CA"),
        "MSFT": (47.64, -122.13, "Redmond, WA"),
        "GOOGL": (37.42, -122.08, "Mountain View, CA"),
        "GOOG": (37.42, -122.08, "Mountain View, CA"),
        "AMZN": (47.61, -122.33, "Seattle, WA"),
        "META": (37.48, -122.15, "Menlo Park, CA"),
        "TSLA": (30.22, -97.77, "Austin, TX"),
        "TSM": (24.77, 120.98, "Hsinchu, Taiwan"),
        "ASML": (51.58, 5.53, "Veldhoven, Netherlands"),
        "AMD": (37.38, -121.96, "Santa Clara, CA"),
        "INTC": (37.39, -121.96, "Santa Clara, CA"),
        "CRM": (37.79, -122.40, "San Francisco, CA"),
        "ORCL": (37.53, -122.26, "Redwood City, CA"),
        "NFLX": (37.26, -121.97, "Los Gatos, CA"),
        "UBER": (37.77, -122.42, "San Francisco, CA"),
        "SNAP": (34.02, -118.49, "Santa Monica, CA"),
        "LYFT": (37.77, -122.42, "San Francisco, CA"),
        "TWLO": (37.79, -122.39, "San Francisco, CA"),
        "SNOW": (37.38, -121.97, "San Mateo, CA"),
        "PLTR": (37.78, -122.39, "Denver, CO"),
        "RBLX": (37.53, -122.25, "San Mateo, CA"),
        # === US FINANCE ===
        "JPM": (40.71, -74.01, "New York, NY"),
        "BAC": (35.23, -80.84, "Charlotte, NC"),
        "GS": (40.71, -74.01, "New York, NY"),
        "MS": (40.71, -74.01, "New York, NY"),
        "V": (37.53, -122.25, "Foster City, CA"),
        "MA": (40.77, -73.97, "New York, NY"),
        "BRK-B": (41.26, -95.94, "Omaha, NE"),
        "WFC": (37.77, -122.42, "San Francisco, CA"),
        "C": (40.71, -74.01, "New York, NY"),
        "AXP": (40.76, -73.97, "New York, NY"),
        # === US OTHER ===
        "WMT": (36.37, -94.21, "Bentonville, AR"),
        "JNJ": (40.48, -74.26, "New Brunswick, NJ"),
        "PG": (39.10, -84.51, "Cincinnati, OH"),
        "XOM": (32.41, -95.94, "Irving, TX"),
        "CVX": (37.76, -122.24, "San Ramon, CA"),
        "UNH": (44.94, -93.33, "Minnetonka, MN"),
        "LLY": (39.78, -86.15, "Indianapolis, IN"),
        "PFE": (40.75, -73.99, "New York, NY"),
        "ABBV": (41.89, -87.94, "North Chicago, IL"),
        "MRK": (40.69, -74.40, "Rahway, NJ"),
        # === INDIA - NSE (.NS) ===
        "RELIANCE.NS": (19.08, 72.88, "Mumbai, India"),
        "TCS.NS": (19.08, 72.88, "Mumbai, India"),
        "INFY.NS": (12.97, 77.59, "Bangalore, India"),
        "HDFCBANK.NS": (19.08, 72.88, "Mumbai, India"),
        "ICICIBANK.NS": (19.08, 72.88, "Mumbai, India"),
        "HINDUNILVR.NS": (19.08, 72.88, "Mumbai, India"),
        "ITC.NS": (22.57, 88.36, "Kolkata, India"),
        "SBIN.NS": (19.08, 72.88, "Mumbai, India"),
        "BHARTIARTL.NS": (28.63, 77.22, "New Delhi, India"),
        "KOTAKBANK.NS": (19.08, 72.88, "Mumbai, India"),
        "LT.NS": (19.08, 72.88, "Mumbai, India"),
        "HCLTECH.NS": (28.57, 77.32, "Noida, India"),
        "AXISBANK.NS": (19.08, 72.88, "Mumbai, India"),
        "WIPRO.NS": (12.97, 77.59, "Bangalore, India"),
        "ASIANPAINT.NS": (19.08, 72.88, "Mumbai, India"),
        "MARUTI.NS": (28.46, 77.03, "Gurgaon, India"),
        "TATAMOTORS.NS": (19.08, 72.88, "Mumbai, India"),
        "TATASTEEL.NS": (22.80, 86.20, "Jamshedpur, India"),
        "SUNPHARMA.NS": (19.08, 72.88, "Mumbai, India"),
        "BAJFINANCE.NS": (18.52, 73.85, "Pune, India"),
        "TITAN.NS": (12.97, 77.59, "Bangalore, India"),
        "ADANIENT.NS": (23.03, 72.57, "Ahmedabad, India"),
        "ADANIPORTS.NS": (23.03, 72.57, "Ahmedabad, India"),
        "ZOMATO.NS": (28.46, 77.03, "Gurgaon, India"),
        "PAYTM.NS": (28.57, 77.32, "Noida, India"),
        "DMART.NS": (19.08, 72.88, "Mumbai, India"),
        "HAL.NS": (12.97, 77.59, "Bangalore, India"),
        "BEL.NS": (12.97, 77.59, "Bangalore, India"),
        "IRCTC.NS": (28.63, 77.22, "New Delhi, India"),
        "ONGC.NS": (28.63, 77.22, "New Delhi, India"),
        "NTPC.NS": (28.63, 77.22, "New Delhi, India"),
        "POWERGRID.NS": (28.63, 77.22, "New Delhi, India"),
        "JSWSTEEL.NS": (19.08, 72.88, "Mumbai, India"),
        "TECHM.NS": (18.52, 73.85, "Pune, India"),
        "DRREDDY.NS": (17.36, 78.47, "Hyderabad, India"),
        "CIPLA.NS": (19.08, 72.88, "Mumbai, India"),
        "DIVISLAB.NS": (17.36, 78.47, "Hyderabad, India"),
        "APOLLOHOSP.NS": (13.08, 80.27, "Chennai, India"),
        "NESTLEIND.NS": (19.08, 72.88, "Mumbai, India"),
        "BRITANNIA.NS": (12.97, 77.59, "Bangalore, India"),
        "NYKAA.NS": (19.08, 72.88, "Mumbai, India"),
        "COALINDIA.NS": (22.57, 88.36, "Kolkata, India"),
        "BAJFINSV.NS": (18.52, 73.85, "Pune, India"),
        "INDUSINDBK.NS": (19.08, 72.88, "Mumbai, India"),
        "GRASIM.NS": (23.03, 72.57, "Ahmedabad, India"),
        "ULTRACEMCO.NS": (19.08, 72.88, "Mumbai, India"),
        "HINDALCO.NS": (19.08, 72.88, "Mumbai, India"),
        # === INDIA - BSE (.BO) ===
        "RELIANCE.BO": (19.08, 72.88, "Mumbai, India"),
        "TCS.BO": (19.08, 72.88, "Mumbai, India"),
        "INFY.BO": (12.97, 77.59, "Bangalore, India"),
        "HDFCBANK.BO": (19.08, 72.88, "Mumbai, India"),
        # === GLOBAL ===
        "SAMSUNG": (37.56, 126.98, "Seoul, South Korea"),
        "005930.KS": (37.56, 126.98, "Seoul, South Korea"),
        "BABA": (30.27, 120.15, "Hangzhou, China"),
        "TCEHY": (22.54, 114.05, "Shenzhen, China"),
        "SAP": (49.29, 8.64, "Walldorf, Germany"),
        "TM": (35.05, 137.16, "Toyota City, Japan"),
        "SONY": (35.62, 139.74, "Tokyo, Japan"),
        "NESN": (46.88, 6.91, "Vevey, Switzerland"),
        "HSBA": (51.51, -0.08, "London, UK"),
    }
    
    t = ticker.upper()
    if t in HQ_DB:
        return HQ_DB[t]
    
    # Try matching base ticker without suffix
    base = t.split(".")[0]
    for key in HQ_DB:
        if key.startswith(base + ".") or key == base:
            return HQ_DB[key]
    
    # Default by suffix
    if ".NS" in t or ".BO" in t:
        return (19.08, 72.88, f"{city or 'Mumbai'}, {country or 'India'} (estimated)")
    if ".L" in t:
        return (51.50, -0.12, f"{city or 'London'}, {country or 'UK'} (estimated)")
    if ".T" in t:
        return (35.67, 139.65, f"{city or 'Tokyo'}, {country or 'Japan'} (estimated)")
    if ".KS" in t:
        return (37.56, 126.98, f"{city or 'Seoul'}, {country or 'South Korea'} (estimated)")
        
    # Ultimate dynamic fallback
    loc_str = ""
    if city: loc_str += city
    if country: loc_str += (", " if loc_str else "") + country
    if not loc_str: loc_str = "USA"
    return (37.77, -122.42, f"{loc_str} (fallback)")



def compute_valuation(company: CompanyData, chaos: float, risk_severity: float) -> SimpleValuation:
    """
    Institutional-grade valuation with proper methodology routing.
    KEY RULE: Fair value should NOT exceed 1.5x current market price in base case.
    The market is generally efficient for large caps. Our job is to stress DOWN, not find upside.
    """
    price = company.current_price
    if price <= 0:
        price = company.market_cap / max(company.shares_outstanding, 1)

    shares = max(company.shares_outstanding, 1)
    net_debt = company.total_debt - company.cash

    sector_lower = (company.sector or "").lower()
    industry_lower = (company.industry or "").lower()

    is_financial = any(x in sector_lower for x in ["financial", "bank", "insurance"]) or \
                   any(x in industry_lower for x in ["bank", "insurance", "capital markets", "credit"])
    is_high_growth = company.revenue_growth > 0.25 and (company.net_income <= 0 or
                     (company.net_income / max(company.revenue, 1)) < 0.10)
    is_cyclical = any(x in sector_lower for x in ["energy", "basic materials", "mining", "utilities"]) or \
                  any(x in industry_lower for x in ["oil", "gas", "mining", "steel", "chemical"])
    is_mature_profitable = not is_financial and not is_high_growth and not is_cyclical and \
                           company.ebitda > 0 and company.net_income > 0

    base_discount_rate = 0.09 + company.beta * 0.04

    if is_financial:
        method = "P/BV + Excess Return (Financial)"
        book_per_share = (company.market_cap * 0.55) / shares
        roe_estimate = company.net_income / max(company.market_cap * 0.55, 1)
        cost_of_equity = 0.08 + company.beta * 0.04
        base_discount_rate = cost_of_equity
        if roe_estimate > cost_of_equity:
            justified_pbv = 1.0 + (roe_estimate - cost_of_equity) / cost_of_equity * 2
        else:
            justified_pbv = max(0.5, roe_estimate / cost_of_equity)
        justified_pbv = min(justified_pbv, 2.5)
        base_fv = book_per_share * justified_pbv
        cross_check = {"P/BV Model": f"${base_fv:.2f}", "Justified P/BV": f"{justified_pbv:.2f}x"}

    elif is_high_growth:
        method = "EV/Revenue (High Growth)"
        growth_pct = company.revenue_growth * 100
        margin_pct = (company.net_income / max(company.revenue, 1)) * 100
        rule_of_40 = growth_pct + margin_pct
        if rule_of_40 > 60: ev_rev = 12.0
        elif rule_of_40 > 40: ev_rev = 8.0
        elif rule_of_40 > 20: ev_rev = 5.0
        else: ev_rev = 3.0
        if company.market_cap > 500e9: ev_rev *= 0.75
        elif company.market_cap > 100e9: ev_rev *= 0.85
        ev = company.revenue * ev_rev
        base_fv = max((ev - net_debt) / shares, 0)
        cross_check = {"EV/Revenue": f"{ev_rev:.1f}x", "Rule of 40": f"{rule_of_40:.0f}"}
        base_discount_rate = 0.10 + company.beta * 0.05

    elif is_cyclical:
        method = "Normalized EBITDA (Mid-Cycle)"
        norm_factor = 0.80
        ev_multiple = 7.0 if "energy" in sector_lower else 6.5
        normalized_ebitda = company.ebitda * norm_factor
        ev = normalized_ebitda * ev_multiple
        base_fv = max((ev - net_debt) / shares, 0)
        cross_check = {"EV/EBITDA": f"{ev_multiple:.1f}x", "Norm Factor": f"{norm_factor:.0%}"}
        base_discount_rate = 0.08 + company.beta * 0.04

    elif is_mature_profitable:
        method = "5-Year FCF-DCF + Gordon Growth"
        capex_intensity = 0.40 if "semiconductor" in industry_lower or "tech" in sector_lower else 0.35
        fcf = company.ebitda * (1 - capex_intensity)
        risk_free = 0.043
        erp = 0.055
        cost_of_equity = risk_free + company.beta * erp
        equity_weight = company.market_cap / max(company.market_cap + company.total_debt, 1)
        debt_weight = 1 - equity_weight
        wacc = equity_weight * cost_of_equity + debt_weight * 0.05 * 0.79
        wacc = max(wacc, 0.07)
        base_discount_rate = wacc
        near_growth = min(company.revenue_growth, 0.10)
        terminal_growth = 0.025
        pv_fcf = 0
        proj_fcf = fcf
        for yr in range(1, 6):
            g = near_growth * (1 - yr * 0.12)
            proj_fcf *= (1 + max(g, 0.02))
            pv_fcf += proj_fcf / (1 + wacc) ** yr
        terminal_fcf = proj_fcf * (1 + terminal_growth)
        tv = terminal_fcf / max(wacc - terminal_growth, 0.03)
        pv_tv = tv / (1 + wacc) ** 5
        ev = pv_fcf + pv_tv
        base_fv = max((ev - net_debt) / shares, 0)
        cross_check = {"WACC": f"{wacc*100:.1f}%", "FCF Y1": f"${fcf/1e9:.1f}B",
                       "Terminal%": f"{pv_tv/max(ev,1)*100:.0f}%"}

    else:
        method = "EV/Revenue (Fallback)"
        ev_rev = 2.0 + max(0, company.revenue_growth * 5)
        ev_rev = min(ev_rev, 5.0)
        ev = company.revenue * ev_rev
        base_fv = max((ev - net_debt) / shares, price * 0.8)
        cross_check = {"EV/Revenue": f"{ev_rev:.1f}x"}
        base_discount_rate = 0.09 + company.beta * 0.04

    # CRITICAL: Anchor fair value to market price (market is efficient for large caps)
    if company.market_cap > 100e9:
        max_fv = price * 1.20
    elif company.market_cap > 10e9:
        max_fv = price * 1.35
    else:
        max_fv = price * 1.50
    min_fv = price * 0.85
    base_fv = max(min(base_fv, max_fv), min_fv)

    # Apply stress
    rev_haircut = chaos * 15 + (risk_severity / 10) * 12
    wacc_stress = chaos * 4.5 + (risk_severity / 10) * 3
    margin_bps = chaos * 250 + risk_severity * 50
    mult_compress = 1 - (chaos * 0.18 + (risk_severity / 10) * 0.12)
    mult_compress = max(mult_compress, 0.45)
    stress_mult = (1 - rev_haircut / 100) * mult_compress
    stress_mult = max(stress_mult, 0.20)
    distressed = base_fv * stress_mult

    # CRITICAL: Downside must always be negative (stress test goes DOWN)
    downside = ((distressed - price) / price) * 100
    if downside > 0:
        min_downside = -(chaos * 40 + risk_severity * 3)
        distressed = price * (1 + min_downside / 100)
        downside = min_downside

    rev_impact = -(base_fv * rev_haircut / 100)
    margin_impact = -(base_fv * margin_bps / 8000)
    mult_impact = -(base_fv * (1 - mult_compress))
    wacc_impact = -(base_fv * wacc_stress / 100)

    waterfall = [
        {"label": "Base Fair Value", "value": round(base_fv, 2), "type": "absolute"},
        {"label": "Revenue Stress", "value": round(rev_impact, 2), "type": "relative"},
        {"label": "Margin Crush", "value": round(margin_impact, 2), "type": "relative"},
        {"label": "Multiple Compression", "value": round(mult_impact, 2), "type": "relative"},
        {"label": "WACC Premium", "value": round(wacc_impact, 2), "type": "relative"},
        {"label": "Distressed Value", "value": round(distressed, 2), "type": "total"},
    ]
    display_wacc = base_discount_rate * 100

    return SimpleValuation(
        current_price=round(price, 2),
        base_fair_value=round(base_fv, 2),
        distressed_value=round(distressed, 2),
        downside_pct=round(downside, 1),
        valuation_method=method,
        base_wacc=round(display_wacc, 2),
        stressed_wacc=round(display_wacc + wacc_stress, 2),
        revenue_haircut=round(rev_haircut, 1),
        margin_compression_bps=round(margin_bps, 0),
        waterfall_data=waterfall,
        method_values=cross_check
    )


# ===============================================================
# VISUALIZATION
# ===============================================================

def curved_path(lat1, lon1, lat2, lon2, n=35):
    """Generate parabolic arc between two points."""
    lats, lons = [], []
    for i in range(n + 1):
        t = i / n
        lat = lat1 + t * (lat2 - lat1)
        lon = lon1 + t * (lon2 - lon1)
        
        # Parabolic arc
        dist = math.sqrt((lat2 - lat1)**2 + (lon2 - lon1)**2)
        arc = dist * 0.12
        curve = 4 * t * (1 - t)
        
        # Perpendicular offset
        dx, dy = lat2 - lat1, lon2 - lon1
        length = math.sqrt(dx**2 + dy**2) or 1
        lat += (-dy / length) * arc * curve
        lon += (dx / length) * arc * curve
        
        lats.append(lat)
        lons.append(lon)
    return lats, lons


def render_map(nodes: List[FractureNode], hq: Tuple[float, float, str]):
    """Render the fracture map with curved convergence lines."""
    
    if not nodes:
        st.info("[MAP] No fracture nodes identified yet.")
        return
    
    fig = go.Figure()
    hq_lat, hq_lon, hq_label = hq
    
    colors = {"critical": "#FF1744", "high": "#FF6D00", "elevated": "#FFD600", "monitoring": "#00E676"}
    
    # 1. Curved lines to HQ
    for node in nodes:
        clats, clons = curved_path(node.latitude, node.longitude, hq_lat, hq_lon)
        c = colors.get(node.threat_level, "#FF6D00")
        opacity = 0.2 + (node.severity / 10) * 0.4
        width = 1 + (node.severity / 10) * 1.5
        
        fig.add_trace(go.Scattermapbox(
            lat=clats, lon=clons, mode="lines",
            line=dict(width=width, color=f"rgba({int(c[1:3],16)},{int(c[3:5],16)},{int(c[5:7],16)},{opacity})"),
            hoverinfo="none", showlegend=False
        ))
    
    # 2. HQ marker (concentric pulse)
    for size, op in [(32, 0.06), (20, 0.15), (12, 0.9)]:
        fig.add_trace(go.Scattermapbox(
            lat=[hq_lat], lon=[hq_lon], mode="markers",
            marker=dict(size=size, color=f"rgba(0,176,255,{op})"),
            showlegend=False, hoverinfo="none" if size > 12 else "text",
            hovertext=f"HQ: {hq_label}" if size == 12 else None,
            name="HQ" if size == 12 else None,
        ))
    # HQ text
    fig.add_trace(go.Scattermapbox(
        lat=[hq_lat], lon=[hq_lon], mode="text",
        text=["HQ"], textposition="bottom center",
        textfont=dict(size=10, color="#00B0FF", family="Arial Black"),
        showlegend=False, hoverinfo="none"
    ))
    
    # 3. Risk nodes by threat level
    for level in ["critical", "high", "elevated", "monitoring"]:
        level_nodes = [n for n in nodes if n.threat_level == level]
        if not level_nodes:
            continue
        
        c = colors[level]
        
        # Glow for critical/high
        if level in ["critical", "high"]:
            fig.add_trace(go.Scattermapbox(
                lat=[n.latitude for n in level_nodes],
                lon=[n.longitude for n in level_nodes],
                mode="markers",
                marker=dict(size=[n.severity * 4 for n in level_nodes], color=f"rgba({int(c[1:3],16)},{int(c[3:5],16)},{int(c[5:7],16)},0.12)"),
                showlegend=False, hoverinfo="none"
            ))
        
        # Main markers — word-wrap description for clean hover display
        def wrap_description(desc, width=55):
            """Wrap description text for hover display."""
            words = desc.split()
            lines = []
            current = ""
            for word in words:
                if len(current) + len(word) + 1 > width:
                    lines.append(current.strip())
                    current = word
                    if len(lines) >= 3:
                        break
                else:
                    current += " " + word
            if current.strip() and len(lines) < 3:
                lines.append(current.strip())
            
            # Always end with ..... if description was truncated
            total_shown = sum(len(l) for l in lines)
            if total_shown < len(desc) - 5:
                if lines:
                    lines[-1] = lines[-1][:width - 5].rstrip() + "....."
            return "<br>".join(lines)

        hover_texts = []
        for n in level_nodes:
            wrapped = wrap_description(n.description, 55)
            ht = (
                f"<b>{n.label}</b><br>"
                f"<br>"
                f"Severity: {n.severity:.1f}/10<br>"
                f"Probability: {n.probability:.0%}<br>"
                f"Domain: {n.category}<br>"
                f"Revenue at Risk: {n.revenue_at_risk_pct:.0f}%<br>"
                f"<br>"
                f"{wrapped}"
            )
            hover_texts.append(ht)

        fig.add_trace(go.Scattermapbox(
            lat=[n.latitude for n in level_nodes],
            lon=[n.longitude for n in level_nodes],
            mode="markers+text",
            marker=dict(
                size=[max(10, 8 + n.severity * 2) for n in level_nodes],
                color=c, opacity=0.85
            ),
            text=[n.label for n in level_nodes],
            textposition="top center",
            textfont=dict(size=9, color=c),
            hovertext=hover_texts,
            hoverinfo="text",
            name=f"{level.upper()} ({len(level_nodes)})",
            showlegend=True,
            hoverlabel=dict(
                bgcolor="#0d1117",
                bordercolor=c,
                font=dict(family="JetBrains Mono, monospace", size=11, color="#e0e0e0"),
                align="left",
                namelength=-1
            )
        ))
    
    # Layout
    all_lats = [n.latitude for n in nodes] + [hq_lat]
    all_lons = [n.longitude for n in nodes] + [hq_lon]
    center_lat = sum(all_lats) / len(all_lats)
    center_lon = sum(all_lons) / len(all_lons)
    spread = max(max(all_lats) - min(all_lats), max(all_lons) - min(all_lons))
    zoom = 0.8 if spread > 120 else 1.5 if spread > 60 else 2.5 if spread > 30 else 3.5
    
    fig.update_layout(
        mapbox=dict(
            style="carto-darkmatter",
            center=dict(lat=center_lat, lon=center_lon),
            zoom=zoom,
            bounds=dict(west=-180, east=180, south=-70, north=80)
        ),
        showlegend=True,
        legend=dict(bgcolor="rgba(12,16,24,0.9)", bordercolor="#1a2538", font=dict(color="#c8d6e5", size=10), x=0.01, y=0.99),
        margin=dict(l=0, r=0, t=0, b=0),
        height=480,
        paper_bgcolor="#080b10",
        dragmode="pan"
    )
    
    st.plotly_chart(fig, use_container_width=True, config={
        "displayModeBar": True,
        "displaylogo": False,
        "scrollZoom": True,
        "modeBarButtonsToRemove": ["select2d", "lasso2d", "resetScale2d"]
    })


# ============================================================
# CONTAGION CASCADE ENGINE
# ============================================================

def generate_contagion_chains(ai, company, validated_risks, chaos_level):
    """
    For top 3 risks by severity, generate second and third-order effects.
    Models how a single shock propagates through the company's financial structure.
    """
    if not validated_risks:
        return []

    sorted_risks = sorted(validated_risks, key=lambda r: float(r.get('severity_score', r.get('severity', 5))), reverse=True)[:3]

    company_name = getattr(company, 'name', 'the company')
    sector = getattr(company, 'sector', 'general') or 'general'
    revenue = getattr(company, 'revenue', 0) or 0
    debt = getattr(company, 'total_debt', 0) or 0
    net_income = getattr(company, 'net_income', 0) or 0
    margin = net_income / max(revenue, 1)

    def risk_title(r):
        return r.get('risk_description', r.get('title', 'Unknown'))[:60]

    prompt = f"""You are a financial contagion analyst. For each primary risk event below,
model the CAUSAL CHAIN of how it propagates through {company_name}'s financial structure.

Company Context:
- Sector: {sector}
- Revenue: ${revenue/1e9:.1f}B
- Debt: ${debt/1e9:.1f}B
- Profit Margin: {margin*100:.1f}%
- Chaos/Stress Level: {chaos_level:.2f}

For each primary risk, provide EXACTLY 3 propagation steps (second-order, third-order, fourth-order effects).
Each step: what breaks next, quantified impact estimate, time delay.

Primary Risks:
{chr(10).join([f"{i+1}. {risk_title(r)} (Severity: {r.get('severity_score', r.get('severity', 5))}/10)" for i, r in enumerate(sorted_risks)])}

Return ONLY valid JSON:
{{
  "chains": [
    {{
      "primary_risk": "name of trigger event",
      "primary_severity": 7,
      "cascade": [
        {{"order": 2, "effect": "second-order effect", "metric_impacted": "e.g. COGS", "magnitude": "e.g. +15%", "time_delay": "2-4 weeks", "cumulative_value_destruction_pct": 5.0}},
        {{"order": 3, "effect": "third-order effect", "metric_impacted": "e.g. Credit Rating", "magnitude": "1-notch downgrade", "time_delay": "1-3 months", "cumulative_value_destruction_pct": 12.0}},
        {{"order": 4, "effect": "fourth-order effect", "metric_impacted": "e.g. Refinancing Cost", "magnitude": "+200bps", "time_delay": "3-6 months", "cumulative_value_destruction_pct": 20.0}}
      ]
    }}
  ]
}}"""

    try:
        response = run_with_timeout(
            ai.generate, kwargs={"prompt": prompt, "temperature": 0.5, "json_mode": True, "max_tokens": 2000},
            timeout=40, default=None
        )
        chains_data = parse_json_safe(response)
        if chains_data and 'chains' in chains_data and len(chains_data['chains']) >= 1:
            return chains_data['chains']
    except Exception:
        pass

    return generate_fallback_chains(sorted_risks, sector, chaos_level)


def generate_fallback_chains(risks, sector, chaos_level):
    """Intelligent fallback contagion chains based on sector patterns."""
    sector_lower = (sector or '').lower()

    if any(k in sector_lower for k in ['energy', 'oil', 'gas']):
        template = [
            {"order": 2, "effect": "Input cost spike forces margin compression", "metric_impacted": "Operating Margin",
             "magnitude": f"-{int(chaos_level*800+200)}bps", "time_delay": "1-2 weeks",
             "cumulative_value_destruction_pct": round(chaos_level * 8 + 3, 1)},
            {"order": 3, "effect": "Credit agencies place on negative watch", "metric_impacted": "Credit Rating",
             "magnitude": "Negative outlook", "time_delay": "4-8 weeks",
             "cumulative_value_destruction_pct": round(chaos_level * 15 + 6, 1)},
            {"order": 4, "effect": "Debt refinancing costs spike, capex cuts forced", "metric_impacted": "Capex Budget",
             "magnitude": f"-{int(chaos_level*30+10)}% cut", "time_delay": "2-4 months",
             "cumulative_value_destruction_pct": round(chaos_level * 22 + 10, 1)},
        ]
    elif any(k in sector_lower for k in ['tech', 'software', 'semiconductor']):
        template = [
            {"order": 2, "effect": "Supply chain disruption delays product launches", "metric_impacted": "Revenue Growth",
             "magnitude": f"-{int(chaos_level*500+100)}bps", "time_delay": "2-6 weeks",
             "cumulative_value_destruction_pct": round(chaos_level * 7 + 2, 1)},
            {"order": 3, "effect": "Market share loss as competitors fill gap", "metric_impacted": "Market Share",
             "magnitude": f"-{int(chaos_level*3+1)}% share", "time_delay": "1-3 months",
             "cumulative_value_destruction_pct": round(chaos_level * 14 + 5, 1)},
            {"order": 4, "effect": "Talent attrition as stock compensation falls underwater", "metric_impacted": "R&D Productivity",
             "magnitude": f"{int(chaos_level*15+5)}% attrition spike", "time_delay": "3-6 months",
             "cumulative_value_destruction_pct": round(chaos_level * 20 + 8, 1)},
        ]
    elif any(k in sector_lower for k in ['bank', 'financial', 'insurance']):
        template = [
            {"order": 2, "effect": "Deposit flight / AUM redemptions accelerate", "metric_impacted": "Funding Cost",
             "magnitude": f"+{int(chaos_level*150+50)}bps", "time_delay": "Days to weeks",
             "cumulative_value_destruction_pct": round(chaos_level * 10 + 4, 1)},
            {"order": 3, "effect": "Forced asset sales at distressed prices", "metric_impacted": "Book Value",
             "magnitude": f"-{int(chaos_level*12+4)}% writedown", "time_delay": "2-6 weeks",
             "cumulative_value_destruction_pct": round(chaos_level * 18 + 8, 1)},
            {"order": 4, "effect": "Counterparty contagion triggers collateral calls", "metric_impacted": "Liquidity Ratio",
             "magnitude": "Below regulatory minimum", "time_delay": "1-3 months",
             "cumulative_value_destruction_pct": round(chaos_level * 28 + 12, 1)},
        ]
    else:
        template = [
            {"order": 2, "effect": "Revenue decline triggers cost restructuring", "metric_impacted": "Operating Costs",
             "magnitude": f"+{int(chaos_level*500+200)}bps as % of revenue", "time_delay": "1-4 weeks",
             "cumulative_value_destruction_pct": round(chaos_level * 7 + 3, 1)},
            {"order": 3, "effect": "Supplier tightens payment terms, working capital strain", "metric_impacted": "Working Capital",
             "magnitude": f"{int(chaos_level*20+10)} days DSO increase", "time_delay": "1-3 months",
             "cumulative_value_destruction_pct": round(chaos_level * 13 + 6, 1)},
            {"order": 4, "effect": "Dividend cut / buyback suspension signals distress", "metric_impacted": "Investor Confidence",
             "magnitude": "Multiple de-rating", "time_delay": "3-6 months",
             "cumulative_value_destruction_pct": round(chaos_level * 20 + 9, 1)},
        ]

    chains = []
    for risk in risks[:3]:
        chains.append({
            "primary_risk": risk.get('risk_description', risk.get('title', 'Unknown Risk'))[:70],
            "primary_severity": float(risk.get('severity_score', risk.get('severity', 6))),
            "cascade": template
        })
    return chains


def render_contagion_section(chains, chaos_level):
    """Render the Contagion Cascade visualization section."""
    st.markdown('<div class="section-hdr">Contagion Cascade -- Second-Order Propagation Model</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="info-panel" style="margin-bottom:16px; border-left: 3px solid #ff6d00">
        <span style="color:#ff6d00; font-family:monospace; font-size:0.8em">[THEORY]</span>
        <span style="color:#7a8b9a; font-size:0.85em; margin-left:8px">
        In crisis regimes, asset correlations converge to 1. Individual risks do not remain isolated --
        they propagate through financial linkages, supplier networks, and investor psychology.
        This model traces causal chains from primary shock to terminal value destruction.
        </span>
    </div>
    """, unsafe_allow_html=True)

    if not chains:
        st.markdown('<div class="info-panel" style="color:#5a6f82">No contagion chains generated. Increase chaos level or re-run analysis.</div>', unsafe_allow_html=True)
        return

    for idx, chain in enumerate(chains):
        primary = chain.get('primary_risk', 'Unknown')[:70]
        severity = chain.get('primary_severity', 6)
        cascade = chain.get('cascade', [])

        final_destruction = cascade[-1].get('cumulative_value_destruction_pct', 10) if cascade else 10
        if final_destruction > 20:
            chain_color = "#ff4444"
            chain_label = "CRITICAL CHAIN"
        elif final_destruction > 12:
            chain_color = "#ff8c00"
            chain_label = "SEVERE CHAIN"
        else:
            chain_color = "#ffaa00"
            chain_label = "MODERATE CHAIN"

        st.markdown(f"""
        <div class="info-panel" style="border-left: 3px solid {chain_color}; margin-bottom: 6px">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px">
                <span style="color:{chain_color}; font-family:monospace; font-size:0.85em; font-weight:bold">
                    CHAIN {idx+1}: {primary}
                </span>
                <span style="color:{chain_color}; font-family:monospace; font-size:0.75em; border:1px solid {chain_color}; padding:2px 6px">
                    {chain_label}
                </span>
            </div>
            <div style="color:#5a6f82; font-size:0.8em; margin-bottom:10px">
                Primary Severity: {severity}/10 | Terminal Value Destruction: -{final_destruction:.1f}%
            </div>
        """, unsafe_allow_html=True)

        # Cascade steps
        for step_idx, step in enumerate(cascade):
            order = step.get('order', step_idx + 2)
            effect = step.get('effect', 'Unknown effect')
            metric = step.get('metric_impacted', 'N/A')
            magnitude = step.get('magnitude', 'N/A')
            time_delay = step.get('time_delay', 'N/A')
            cum_dest = step.get('cumulative_value_destruction_pct', 0)
            bar_w = min(int(cum_dest * 4), 100)
            step_color = "#ff4444" if step_idx == 2 else "#ff8c00" if step_idx == 1 else "#ffaa00"

            arrow = "&gt;&gt;&gt;" if step_idx == 0 else "&nbsp;&nbsp;&gt;&gt;&gt;"
            st.markdown(f"""
            <div style="display:flex; align-items:flex-start; margin:4px 0; padding:6px 8px; background:rgba(255,255,255,0.03); border-radius:4px">
                <div style="min-width:28px; color:{step_color}; font-family:monospace; font-size:0.8em; font-weight:bold; margin-right:8px">
                    [{order}]
                </div>
                <div style="flex:1">
                    <div style="color:#c8d6e5; font-size:0.85em">{arrow} {effect}</div>
                    <div style="color:#5a6f82; font-size:0.78em; margin-top:3px">
                        {metric}: <span style="color:{step_color}">{magnitude}</span>
                        &nbsp;| Delay: {time_delay}
                        &nbsp;| Cumulative: <span style="color:{step_color}">-{cum_dest:.1f}%</span>
                    </div>
                    <div style="margin-top:4px; height:3px; background:rgba(255,255,255,0.05); border-radius:2px">
                        <div style="width:{bar_w}%; height:100%; background:{step_color}; border-radius:2px; opacity:0.7"></div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # Compound Contagion Score
    if chains:
        max_dest = max(
            [c.get('cascade', [{}])[-1].get('cumulative_value_destruction_pct', 0) for c in chains if c.get('cascade')],
            default=0
        )
        avg_dest = sum(
            [c.get('cascade', [{}])[-1].get('cumulative_value_destruction_pct', 0) for c in chains if c.get('cascade')]
        ) / max(len(chains), 1)
        compound_factor = 1 + (chaos_level * 0.3 * (len(chains) - 1))
        compound_dest = min(avg_dest * compound_factor, 65)
        rho = min(0.4 + chaos_level * 0.5, 0.95)

        if compound_dest > 30:
            cc_color = "#ff4444"
            cc_status = "SYSTEMIC FAILURE REGIME"
        elif compound_dest > 18:
            cc_color = "#ff8c00"
            cc_status = "CONTAGION AMPLIFICATION"
        else:
            cc_color = "#ffaa00"
            cc_status = "CONTAINED PROPAGATION"

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="info-panel" style="border-left:3px solid {cc_color}; text-align:center">
                <div style="color:#5a6f82; font-family:monospace; font-size:0.75em; margin-bottom:4px">COMPOUND CONTAGION ASSESSMENT</div>
                <div style="color:{cc_color}; font-size:2em; font-weight:bold; font-family:monospace">-{compound_dest:.1f}%</div>
                <div style="color:#5a6f82; font-size:0.78em; margin-top:4px">
                    {len(chains)} active chains | Compound factor: {compound_factor:.2f}x
                </div>
                <div style="color:{cc_color}; font-family:monospace; font-size:0.75em; margin-top:6px">{cc_status}</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="info-panel" style="border-left:3px solid #5a6f82; text-align:center">
                <div style="color:#5a6f82; font-family:monospace; font-size:0.75em; margin-bottom:4px">CRISIS CORRELATION</div>
                <div style="color:#c8d6e5; font-size:2em; font-weight:bold; font-family:monospace">rho = {rho:.2f}</div>
                <div style="color:#5a6f82; font-size:0.78em; margin-top:4px">
                    In crisis regimes correlations converge to 1.<br>Diversification breaks down.
                </div>
            </div>
            """, unsafe_allow_html=True)


# ============================================================
# VALUATION TRANSPARENCY ENGINE
# ============================================================

def render_valuation_transparency(company, val, chaos_level, verdicts):
    """Full audit trail: routing, inputs, formula, stress decomposition. Addition only."""

    # --- derive scalars from dataclass objects ---
    name             = getattr(company, "name", "Unknown")
    sector           = getattr(company, "sector", "Unknown") or "Unknown"
    industry         = getattr(company, "industry", "Unknown") or "Unknown"
    market_cap       = getattr(company, "market_cap", 0) or 0
    current_price    = getattr(company, "current_price", 0) or 0
    revenue          = getattr(company, "revenue", 0) or 0
    ebitda           = getattr(company, "ebitda", 0) or 0
    net_income       = getattr(company, "net_income", 0) or 0
    total_debt       = getattr(company, "total_debt", 0) or 0
    cash             = getattr(company, "cash", 0) or 0
    shares           = getattr(company, "shares_outstanding", 1) or 1
    beta             = getattr(company, "beta", 1.0) or 1.0
    rev_growth       = getattr(company, "revenue_growth", 0) or 0
    profit_margin    = net_income / max(revenue, 1)
    fcf              = 0  # not stored on dataclass; derived below
    # Derive book_value and roe the same way compute_valuation does
    book_value       = (market_cap * 0.55) / shares if shares > 0 else 0
    roe              = net_income / max(market_cap * 0.55, 1) if market_cap > 0 else 0

    base_fv    = getattr(val, "base_fair_value", 0) or 0
    distressed = getattr(val, "distressed_value", 0) or 0
    method     = getattr(val, "valuation_method", "Unknown")
    downside   = getattr(val, "downside_pct", 0) or 0

    sector_lower = (sector + " " + industry).lower()
    is_financial   = any(k in sector_lower for k in ["bank", "financial", "insurance", "capital markets"])
    is_cyclical    = any(k in sector_lower for k in ["energy", "oil", "gas", "mining", "materials", "utilities"])
    is_high_growth = (rev_growth > 0.25) and (net_income <= 0 or profit_margin < 0.05)
    is_mature      = (ebitda > 0) and (net_income > 0) and not is_financial and not is_cyclical and not is_high_growth
    is_fallback    = not any([is_financial, is_cyclical, is_high_growth, is_mature])

    if is_financial:
        path_num, path_label, path_color = 1, "FINANCIAL (P/BV + Excess Return)", "#4fc3f7"
    elif is_high_growth:
        path_num, path_label, path_color = 2, "HIGH-GROWTH (EV/Revenue + Rule of 40)", "#ab47bc"
    elif is_mature:
        path_num, path_label, path_color = 3, "MATURE PROFITABLE (5Y FCF-DCF + Gordon)", "#66bb6a"
    elif is_cyclical:
        path_num, path_label, path_color = 4, "CYCLICAL (Normalized Mid-Cycle EBITDA)", "#ffa726"
    else:
        path_num, path_label, path_color = 5, "LOSS-MAKING / FALLBACK (EV/Revenue Capped)", "#ef5350"

    ev = market_cap + total_debt - cash

    # ── SECTION HEADER ──
    st.markdown('<div class="section-hdr">Valuation Transparency -- Methodology and Calculations</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="info-panel" style="border-left:3px solid {path_color}; margin-bottom:12px">
        <span style="color:#5a6f82; font-family:monospace; font-size:0.78em">Full audit trail of routing logic, formulas applied, and stress parameters. All figures USD. No black boxes.</span>
    </div>
    """, unsafe_allow_html=True)

    # ── [1] ROUTING DECISION ──
    st.markdown(f"""
    <div class="info-panel" style="margin-bottom:10px">
        <div style="color:{path_color}; font-family:monospace; font-size:0.8em; font-weight:bold; margin-bottom:8px">[1] ROUTING DECISION</div>
        <div class="ws-row"><span class="ws-k">Company</span><span class="ws-v">{name}</span></div>
        <div class="ws-row"><span class="ws-k">Sector / Industry</span><span class="ws-v">{sector} / {industry}</span></div>
        <div class="ws-row"><span class="ws-k">Revenue Growth</span><span class="ws-v">{rev_growth*100:.1f}% {"(>25% threshold)" if rev_growth > 0.25 else "(below 25%)"}</span></div>
        <div class="ws-row"><span class="ws-k">EBITDA</span><span class="ws-v">{"$"+f"{ebitda/1e9:.2f}B" if ebitda > 0 else "Negative / N/A"}</span></div>
        <div class="ws-row"><span class="ws-k">Net Income</span><span class="ws-v">{"$"+f"{net_income/1e9:.2f}B" if net_income > 0 else "Negative / N/A"}</span></div>
        <div class="ws-row"><span class="ws-k">Profit Margin</span><span class="ws-v">{profit_margin*100:.1f}%</span></div>
        <div class="ws-row" style="border:none; margin-top:6px">
            <span class="ws-k">Classification</span>
            <span class="ws-v" style="color:{path_color}; font-weight:bold">PATH {path_num} -- {path_label}</span>
        </div>
        <div style="color:#5a6f82; font-size:0.75em; margin-top:6px; font-family:monospace">
            Financial={is_financial} | Cyclical={is_cyclical} | HighGrowth={is_high_growth} | Mature={is_mature} | Fallback={is_fallback}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── [2] RAW INPUTS ──
    c1, c2 = st.columns(2)
    inputs = [
        ("Market Cap", f"${market_cap/1e9:.2f}B"),
        ("Current Price", f"${current_price:.2f}"),
        ("Revenue (TTM)", f"${revenue/1e9:.2f}B"),
        ("EBITDA (TTM)", f"${ ebitda/1e9:.2f}B" if ebitda else "N/A"),
        ("Net Income", f"${net_income/1e9:.2f}B" if net_income else "N/A"),
        ("Total Debt", f"${total_debt/1e9:.2f}B" if total_debt else "N/A"),
        ("Cash & Equiv", f"${cash/1e9:.2f}B" if cash else "N/A"),
        ("Enterprise Value", f"${ev/1e9:.2f}B"),
        ("Shares Out", f"{shares/1e9:.2f}B"),
        ("Beta", f"{beta:.2f}"),
        ("Revenue Growth", f"{rev_growth*100:.1f}%"),
        ("Profit Margin", f"{profit_margin*100:.1f}%"),
    ]
    half = len(inputs) // 2
    with c1:
        rows = "".join(f'<div class="ws-row"><span class="ws-k">{k}</span><span class="ws-v">{v}</span></div>' for k,v in inputs[:half])
        st.markdown(f'<div class="info-panel"><div style="color:#4fc3f7; font-family:monospace; font-size:0.8em; font-weight:bold; margin-bottom:8px">[2] RAW INPUTS</div>{rows}</div>', unsafe_allow_html=True)
    with c2:
        rows = "".join(f'<div class="ws-row"><span class="ws-k">{k}</span><span class="ws-v">{v}</span></div>' for k,v in inputs[half:])
        st.markdown(f'<div class="info-panel"><div style="color:#4fc3f7; font-family:monospace; font-size:0.8em; font-weight:bold; margin-bottom:8px">&nbsp;</div>{rows}</div>', unsafe_allow_html=True)

    # ── [3] PATH-SPECIFIC FORMULA ──
    risk_free, erp = 0.043, 0.055
    coe = risk_free + beta * erp

    if path_num == 1:
        justified_pbv = min(max(roe / coe, 0.5), 2.5) if coe > 0 and roe > 0 else 1.0
        formula_lines = [
            f"CoE = Rf + Beta x ERP = {risk_free:.3f} + {beta:.2f} x {erp:.3f} = {coe*100:.2f}%",
            f"Justified P/BV = ROE / CoE (capped 0.5x-2.5x) = {justified_pbv:.2f}x",
            f"Implied FV = Book Value x {justified_pbv:.2f} = ${book_value * justified_pbv:.2f}",
            "Note: Debt is the product for banks, not a liability. DCF is inapplicable.",
        ]
    elif path_num == 2:
        r40 = (rev_growth * 100) + (profit_margin * 100)
        base_mul = 12.0 if r40 >= 60 else 8.0 if r40 >= 40 else 5.0 if r40 >= 20 else 3.0
        if market_cap > 100e9: base_mul *= 0.7
        elif market_cap > 50e9: base_mul *= 0.85
        implied_ev2 = revenue * base_mul
        implied_eq2 = implied_ev2 - total_debt + cash
        implied_ps2 = implied_eq2 / shares if shares > 0 else current_price
        formula_lines = [
            f"Rule of 40 = RevGrowth% + Margin% = {rev_growth*100:.1f} + {profit_margin*100:.1f} = {r40:.1f}",
            f"EV/Rev Multiple (tier) = {base_mul:.1f}x (after size discount if >$50B mcap)",
            f"Implied EV = ${revenue/1e9:.2f}B x {base_mul:.1f} = ${implied_ev2/1e9:.2f}B",
            f"Per Share = (EV - Debt + Cash) / Shares = ${implied_ps2:.2f}",
        ]
    elif path_num == 3:
        dw = total_debt / (market_cap + total_debt) if (market_cap + total_debt) > 0 else 0.3
        ew = 1 - dw
        kd, tax = 0.05, 0.21
        wacc = ew * coe + dw * kd * (1 - tax)
        ng = min(rev_growth if rev_growth else 0.05, 0.10)
        tg = 0.025
        capex_int = 0.40 if any(k in sector_lower for k in ["semi","tech"]) else 0.35
        base_fcf = ebitda * (1 - capex_int) if ebitda > 0 else revenue * 0.08
        pv_sum = sum([base_fcf * (1 + ng * (1-(i-1)*0.15))**i / (1+wacc)**i for i in range(1,6)])
        tv = base_fcf * (1 + tg) / (wacc - tg) if wacc > tg else base_fcf * 20
        pv_tv = tv / (1+wacc)**5
        total_ev3 = pv_sum + pv_tv
        ps3 = (total_ev3 - total_debt + cash) / shares if shares > 0 else current_price
        formula_lines = [
            f"WACC = {ew:.2f} x {coe*100:.2f}% + {dw:.2f} x {kd:.0%} x (1-{tax:.0%}) = {wacc*100:.2f}%",
            f"Base FCF = EBITDA x (1-{capex_int:.0%} capex) = ${base_fcf/1e9:.2f}B",
            f"PV(5Y FCFs) = ${pv_sum/1e9:.2f}B | TV (Gordon) = ${tv/1e9:.1f}B | PV(TV) = ${pv_tv/1e9:.2f}B",
            f"Total EV = ${total_ev3/1e9:.2f}B --> Per Share = ${ps3:.2f}",
        ]
    elif path_num == 4:
        norm_ebitda = (ebitda if ebitda > 0 else revenue * 0.15) * 0.8
        mul4 = 7.0 if any(k in sector_lower for k in ["energy","oil","petroleum"]) else 6.5
        ps4 = (norm_ebitda * mul4 - total_debt + cash) / shares if shares > 0 else current_price
        formula_lines = [
            "Normalization: Reported EBITDA x 0.80 (mid-cycle haircut)",
            f"Normalized EBITDA = ${norm_ebitda/1e9:.2f}B",
            f"EV/EBITDA Multiple = {mul4:.1f}x (energy=7x, other cyclical=6.5x)",
            f"Per Share = ${ps4:.2f}",
        ]
    else:
        mul5 = min(5.0, max(1.0, rev_growth * 10 if rev_growth else 2.0))
        ps5 = max((revenue * mul5 - total_debt + cash) / shares if shares > 0 else current_price, current_price * 0.8)
        formula_lines = [
            f"EV/Revenue Multiple (capped 1x-5x) = {mul5:.1f}x",
            f"Implied Per Share = ${ps5:.2f} (floored at 0.8x market price)",
            "Note: No stable earnings to discount. Revenue multiple is most honest anchor.",
        ]

    formula_html = "".join(f'<div style="color:#c8d6e5; font-family:monospace; font-size:0.82em; padding:3px 0; border-bottom:1px solid rgba(255,255,255,0.04)">{l}</div>' for l in formula_lines)
    st.markdown(f"""
    <div class="info-panel" style="margin-bottom:10px">
        <div style="color:{path_color}; font-family:monospace; font-size:0.8em; font-weight:bold; margin-bottom:8px">[3] VALUATION FORMULA -- PATH {path_num}</div>
        {formula_html}
    </div>
    """, unsafe_allow_html=True)

    # ── [3.5] RISK SCORING METHODOLOGY ──
    if verdicts:
        avg_sev_35  = sum(v.severity_score for v in verdicts) / len(verdicts)
        avg_prob_35 = sum(v.probability for v in verdicts) / len(verdicts)
        highest_35  = max(verdicts, key=lambda v: v.severity_score)
        st.markdown(f"""
    <div class="info-panel" style="margin-bottom:10px">
        <div style="color:#ab47bc; font-family:monospace; font-size:0.8em; font-weight:bold; margin-bottom:8px">[3.5] RISK SCORING -- ADVERSARIAL TRIBUNAL</div>
        <div style="color:#5a6f82; font-size:0.75em; font-family:monospace; margin-bottom:8px">
            Each risk passes through a 3-agent adversarial debate. Judge calibration:<br>
            8+ = Catastrophic (&gt;25% impairment) | 6-7 = Material | 4-5 = Moderate | &lt;4 = Dismissed
        </div>
        <div class="ws-row"><span class="ws-k">Risks Debated</span><span class="ws-v">{len(verdicts)} validated / debated</span></div>
        <div class="ws-row"><span class="ws-k">Avg Severity (Judge)</span><span class="ws-v">{avg_sev_35:.2f}/10</span></div>
        <div class="ws-row"><span class="ws-k">Avg Probability (Judge)</span><span class="ws-v">{avg_prob_35:.0%}</span></div>
        <div class="ws-row"><span class="ws-k">Highest Threat</span><span class="ws-v" style="color:#ff4444">{highest_35.risk_description[:60]}... ({highest_35.severity_score:.1f}/10)</span></div>
        <div class="ws-row" style="border:none"><span class="ws-k">Judge Temperature</span><span class="ws-v">0.3 (low variance, high conviction)</span></div>
        <div style="color:#5a6f82; font-size:0.74em; font-family:monospace; margin-top:8px">
            Pipeline: Intel Scan (AI + Tavily) → Bear Advocate (T=0.6) → Bull Advocate (T=0.6) → Judge (T=0.3)<br>
            Revenue-at-risk % is set at scan stage, not modified by tribunal.<br>
            Dismissal rule: verdict=DISMISSED AND severity&lt;4 → risk dropped from analysis.
        </div>
    </div>
        """, unsafe_allow_html=True)

    # ── [4] MARKET ANCHORING ──
    if market_cap > 100e9:   cap_label, cap_mul = "LARGE CAP (>$100B)", 1.20
    elif market_cap > 10e9:  cap_label, cap_mul = "MID CAP ($10-100B)", 1.35
    else:                    cap_label, cap_mul = "SMALL CAP (<$10B)", 1.50
    max_allowed = current_price * cap_mul
    was_capped = base_fv < max_allowed * 0.99

    st.markdown(f"""
    <div class="info-panel" style="margin-bottom:10px">
        <div style="color:#66bb6a; font-family:monospace; font-size:0.8em; font-weight:bold; margin-bottom:8px">[4] MARKET ANCHORING -- EFFICIENCY ASSUMPTION</div>
        <div class="ws-row"><span class="ws-k">Size Tier</span><span class="ws-v">{cap_label}</span></div>
        <div class="ws-row"><span class="ws-k">Max Allowed FV</span><span class="ws-v">${current_price:.2f} x {cap_mul:.2f} = ${max_allowed:.2f}</span></div>
        <div class="ws-row" style="border:none"><span class="ws-k">Final Base FV</span>
            <span class="ws-v" style="color:#66bb6a">${base_fv:.2f} {"(CAPPED -- model exceeded anchor)" if was_capped else "(within bounds)"}</span>
        </div>
        <div style="color:#5a6f82; font-size:0.75em; margin-top:6px">
            This is a stress-test tool, not a stock picker. If the model says 2.5x current price, the model is wrong.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── [5] STRESS DECOMPOSITION ──
    avg_sev = sum(v.severity_score for v in verdicts) / max(len(verdicts), 1) if verdicts else 5.0
    rev_hc  = chaos_level * 15 + (avg_sev / 10) * 12
    wacc_p  = chaos_level * 4.5 + (avg_sev / 10) * 3
    mc_bps  = chaos_level * 250 + avg_sev * 50
    mul_c   = 1 - (chaos_level * 0.18 + (avg_sev / 10) * 0.12)
    min_ds  = -(chaos_level * 40 + avg_sev * 3)

    st.markdown(f"""
    <div class="info-panel" style="margin-bottom:10px">
        <div style="color:#ff6d00; font-family:monospace; font-size:0.8em; font-weight:bold; margin-bottom:8px">[5] STRESS DECOMPOSITION -- CHAOS PARAMETER</div>
        <div class="ws-row"><span class="ws-k">Chaos Level</span><span class="ws-v" style="color:#ff6d00">{chaos_level:.2f}</span></div>
        <div class="ws-row"><span class="ws-k">Avg Risk Severity</span><span class="ws-v">{avg_sev:.1f}/10 ({len(verdicts)} risks)</span></div>
        <div class="ws-row"><span class="ws-k">Revenue Haircut</span><span class="ws-v" style="color:#ff4444">-{rev_hc:.1f}% = {chaos_level:.2f}x15 + ({avg_sev:.1f}/10)x12</span></div>
        <div class="ws-row"><span class="ws-k">WACC Premium</span><span class="ws-v" style="color:#ff4444">+{wacc_p:.2f}% = {chaos_level:.2f}x4.5 + ({avg_sev:.1f}/10)x3</span></div>
        <div class="ws-row"><span class="ws-k">Margin Compression</span><span class="ws-v" style="color:#ff4444">-{mc_bps:.0f} bps = {chaos_level:.2f}x250 + {avg_sev:.1f}x50</span></div>
        <div class="ws-row" style="border:none"><span class="ws-k">Multiple Compression</span><span class="ws-v" style="color:#ff4444">{mul_c:.3f}x ({(1-mul_c)*100:.1f}% de-rating)</span></div>
    </div>
    """, unsafe_allow_html=True)

    # ── [6] FINAL OUTPUT ──
    ds_color = "#ff1744" if downside <= -30 else "#ff6d00" if downside <= -15 else "#ffd600"
    st.markdown(f"""
    <div class="info-panel" style="margin-bottom:10px">
        <div style="color:#c8d6e5; font-family:monospace; font-size:0.8em; font-weight:bold; margin-bottom:8px">[6] FINAL OUTPUT</div>
        <div class="ws-row"><span class="ws-k">Current Market Price</span><span class="ws-v">${current_price:.2f}</span></div>
        <div class="ws-row"><span class="ws-k">Base Fair Value (post-cap)</span><span class="ws-v" style="color:#00e676">${base_fv:.2f}</span></div>
        <div class="ws-row"><span class="ws-k">Distressed Value (post-stress)</span><span class="ws-v" style="color:#ff1744">${distressed:.2f}</span></div>
        <div class="ws-row"><span class="ws-k">Implied Downside</span><span class="ws-v" style="color:{ds_color}">{downside:.1f}%</span></div>
        <div class="ws-row" style="border:none"><span class="ws-k">Min Forced Floor</span><span class="ws-v" style="color:#5a6f82">{min_ds:.1f}% (downside always forced negative)</span></div>
    </div>
    """, unsafe_allow_html=True)

    # ── [7] PATH REFERENCE LEGEND ──
    st.markdown("""
    <div class="info-panel">
        <div style="color:#5a6f82; font-family:monospace; font-size:0.8em; font-weight:bold; margin-bottom:8px">[7] ALL VALUATION PATHS -- REFERENCE</div>
        <div style="display:grid; grid-template-columns:40px 120px 1fr 1fr; gap:4px; font-family:monospace; font-size:0.78em">
            <span style="color:#5a6f82">PATH</span><span style="color:#5a6f82">TYPE</span><span style="color:#5a6f82">METHOD</span><span style="color:#5a6f82">WHY NOT DCF</span>
            <span style="color:#4fc3f7">1</span><span>Financial</span><span>P/BV + Excess Return</span><span style="color:#5a6f82">Debt = product, not liability</span>
            <span style="color:#ab47bc">2</span><span>High-Growth</span><span>EV/Revenue + R40</span><span style="color:#5a6f82">Negative FCF, TV >80%</span>
            <span style="color:#66bb6a">3</span><span>Mature</span><span>5Y FCF-DCF + Gordon</span><span style="color:#5a6f82">Only valid DCF candidate</span>
            <span style="color:#ffa726">4</span><span>Cyclical</span><span>Normalized EBITDA</span><span style="color:#5a6f82">Spot earnings mislead at peaks</span>
            <span style="color:#ef5350">5</span><span>Loss-Making</span><span>EV/Revenue (capped)</span><span style="color:#5a6f82">No earnings to discount</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_waterfall(val: SimpleValuation):
    """Waterfall destruction chart."""
    w = val.waterfall_data
    if not w or len(w) < 3:
        return
    
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=[d["type"] for d in w],
        x=[d["label"] for d in w],
        y=[d["value"] for d in w],
        connector=dict(line=dict(color="rgba(80,80,80,0.3)", width=1)),
        decreasing=dict(marker=dict(color="#FF1744")),
        increasing=dict(marker=dict(color="#00E676")),
        totals=dict(marker=dict(color="#FFAB00")),
        textposition="outside",
        text=[f"${abs(d['value']):.2f}" if d['value'] >= 0 else f"-${abs(d['value']):.2f}" for d in w],
        textfont=dict(size=9, color="#c8d6e5", family="monospace"),
    ))
    
    fig.add_hline(y=val.current_price, line_dash="dash", line_color="#448aff", line_width=1.5,
                  annotation_text=f"Market: ${val.current_price:.2f}", annotation_font_color="#448aff", annotation_font_size=10)
    
    fig.update_layout(
        paper_bgcolor="#0c1018",
        plot_bgcolor="#0c1018",
        font=dict(color="#78909c", size=9),
        yaxis=dict(
            gridcolor="#1a2538",
            zerolinecolor="#2a4058",
            title=dict(text="$/Share", font=dict(size=9, color="#5a6f82"))
        ),
        xaxis=dict(
            tickangle=-15,
            tickfont=dict(size=8, color="#78909c")
        ),
        height=340,
        margin=dict(t=15, b=70, l=50, r=15),
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)


def render_risk_cards(verdicts: List[RiskVerdict]):
    """Render risk cards in WorldMonitor style."""
    
    for v in sorted(verdicts, key=lambda x: x.severity_score, reverse=True):
        level = "critical" if v.severity_score >= 8 else "high" if v.severity_score >= 6 else "elevated" if v.severity_score >= 4 else "monitoring"
        level_label = level.upper()
        color = {"critical": "#ff1744", "high": "#ff6d00", "elevated": "#ffd600", "monitoring": "#00e676"}[level]
        
        st.markdown(f"""
        <div class="risk-card risk-{level}">
            <div class="risk-title">{v.risk_description[:80]}</div>
            <div class="risk-meta">
                <span style="color:{color}; font-weight:bold">[{level_label}]</span>
                <span>Severity: {v.severity_score:.1f}/10</span>
                <span>Probability: {v.probability:.0%}</span>
                <span>Revenue Risk: {v.revenue_at_risk_pct:.0f}%</span>
            </div>
            <div class="risk-meta">
                <span>Domain: {v.domain}</span>
                <span>Location: {v.geographic_nexus}</span>
            </div>
            <div class="risk-desc">{v.risk_description}</div>
        </div>
        """, unsafe_allow_html=True)


def render_debate_feed(verdicts: List[RiskVerdict]):
    """Render adversarial debate in terminal style."""
    
    for i, v in enumerate(verdicts):
        level = "critical" if v.severity_score >= 8 else "high" if v.severity_score >= 6 else "elevated"
        with st.expander(f"[{v.severity_score:.1f}] {v.risk_description[:60]}...", expanded=(i == 0)):
            cols = st.columns(4)
            cols[0].markdown(f"""
            <div style="text-align: left; padding-left: 5px;">
                <div style="font-size: 0.85rem; color: #8892b0; font-weight: 500; letter-spacing: 0.05em; margin-bottom: 2px;">Severity</div>
                <div style="font-size: 2.2rem; color: #ffffff; font-weight: 800; line-height: 1;">{v.severity_score:.1f}</div>
            </div>
            """, unsafe_allow_html=True)
            
            cols[1].markdown(f"""
            <div style="text-align: left; padding-left: 5px;">
                <div style="font-size: 0.85rem; color: #8892b0; font-weight: 500; letter-spacing: 0.05em; margin-bottom: 2px;">Probability</div>
                <div style="font-size: 2.2rem; color: #ffffff; font-weight: 800; line-height: 1;">{v.probability:.0%}</div>
            </div>
            """, unsafe_allow_html=True)
            
            cols[2].markdown(f"""
            <div style="text-align: left; padding-left: 5px;">
                <div style="font-size: 0.85rem; color: #8892b0; font-weight: 500; letter-spacing: 0.05em; margin-bottom: 2px;">Rev Risk</div>
                <div style="font-size: 2.2rem; color: #ffffff; font-weight: 800; line-height: 1;">{v.revenue_at_risk_pct:.0f}%</div>
            </div>
            """, unsafe_allow_html=True)
            
            horizon_val = v.time_horizon.replace("_", " ")
            cols[3].markdown(f"""
            <div style="text-align: left; padding-left: 5px;">
                <div style="font-size: 0.85rem; color: #8892b0; font-weight: 500; letter-spacing: 0.05em; margin-bottom: 2px;">Horizon</div>
                <div style="font-size: 2.2rem; color: #ffffff; font-weight: 800; line-height: 1;">{horizon_val}</div>
            </div>
            """, unsafe_allow_html=True)

            
            for msg in v.debate_transcript:
                cls = f"msg-{msg.role}"
                role_name = {"bear": "BEAR ADVOCATE", "bull": "BULL ADVOCATE", "judge": "FRACTURE JUDGE"}.get(msg.role, msg.role.upper())
                st.markdown(f"""
                <div class="debate-msg {cls}">
                    <div class="msg-role">{role_name} | Confidence: {msg.confidence:.0%}</div>
                    {msg.content}
                </div>
                """, unsafe_allow_html=True)


def format_telemetry_dict(data):
    """Format prompt inputs, outputs, and metadata dictionaries into clean, label-based HTML tags (no curly braces)."""
    import json
    if not data:
        return '<span style="color: #5a6f82; font-style: italic;">None</span>'
    
    if not isinstance(data, dict):
        try:
            data = json.loads(data)
        except Exception:
            return f'<span style="color: #eceff1;">{data}</span>'
            
    html_parts = []
    for k, v in data.items():
        # Prettify the key name (replace underscores with spaces, title-case)
        key_title = k.replace("_", " ").title()
        
        # Apply custom formatting based on key patterns
        if "severity" in k.lower() and isinstance(v, (int, float)):
            val_str = f'<span style="color: #ff6d00; font-weight: bold;">{v}/10</span>'
        elif "confidence" in k.lower() and isinstance(v, (int, float)):
            pct = int(v * 100) if v <= 1.0 else int(v)
            val_str = f'<span style="color: #00e676; font-weight: bold;">{pct}%</span>'
        elif isinstance(v, dict):
            val_str = format_telemetry_dict(v)
        else:
            val_str = f'<span style="color: #eceff1;">{v}</span>'
            
        html_parts.append(f"""
        <div style="margin-bottom: 10px; line-height: 1.5;">
            <strong style="color: #00ffd0; font-size: 0.85em; display: block; margin-bottom: 2px; text-transform: uppercase; letter-spacing: 0.5px;">{key_title}</strong>
            <span style="font-size: 0.82em; color: #eceff1;">{val_str}</span>
        </div>
        """)
        
    return "\n".join(html_parts)


def render_arize_telemetry_console():
    """Render live Arize trace spans, prompt inputs, and outputs with dynamic SVG flow animations."""
    import os
    import json
    from arize_mcp_client import GLOBAL_TRACE_CONSOLE

    st.markdown('<div class="section-hdr">Arize Phoenix Live Telemetry Console</div>', unsafe_allow_html=True)

    def clean_html(html_str):
        # Programmatically strip all leading and trailing whitespace on every single line
        # This completely guarantees Streamlit's markdown parser will not treat HTML tags as preformatted blocks
        return "\n".join([line.strip() for line in html_str.split("\n")])

    # Dynamic metrics calculations
    total_traces = len(GLOBAL_TRACE_CONSOLE)
    total_spans = sum(len(t.get('spans', [])) for t in GLOBAL_TRACE_CONSOLE)
    
    endpoint_url = os.getenv("PHOENIX_COLLECTOR_ENDPOINT") or os.getenv("PHOENIX_COLLECTOR_URL") or "http://localhost:6006/v1/traces"
    if "app.phoenix.arize.com" in endpoint_url or os.getenv("ARIZE_API_KEY") or os.getenv("PHOENIX_API_KEY"):
        collector_type = "Arize Phoenix SaaS Cloud"
        status_text = "CONNECTED & RUNNING"
        status_color = "#00ffd0"
    else:
        collector_type = "Phoenix Local Collector"
        status_text = "ACTIVE LOCAL BRIDGE"
        status_color = "#4fc3f7"

    # SVG Telemetry Flow Animation
    svg_html = f"""
    <div class="telemetry-container">
        <div class="telemetry-header">
            <div class="telemetry-title">
                <div class="telemetry-status-pulse"></div>
                Arize Phoenix Telemetry Stream -- Active Ingestion
            </div>
            <div style="font-family: monospace; font-size: 0.7em; background: #1a2538; padding: 2px 8px; border-radius: 4px; color: #eceff1; font-weight: bold;">
                OTLP PROTOBUF / HTTP/1.1
            </div>
        </div>
        
        <svg width="100%" height="90px" viewBox="0 0 600 90" style="background:#0a0e14; border-radius:4px;">
            <defs>
                <linearGradient id="pipe-grad" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stop-color="#ff3344" stop-opacity="0.8"/>
                    <stop offset="50%" stop-color="#9d4edd" stop-opacity="0.8"/>
                    <stop offset="100%" stop-color="#00ffd0" stop-opacity="0.8"/>
                </linearGradient>
                <filter id="glow-cyan" x="-20%" y="-20%" width="140%" height="140%">
                    <feGaussianBlur stdDeviation="3" result="blur" />
                    <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
                <filter id="glow-red" x="-20%" y="-20%" width="140%" height="140%">
                    <feGaussianBlur stdDeviation="3" result="blur" />
                    <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
            </defs>
            
            <!-- Connection Pipeline Background -->
            <path d="M 76,40 Q 300,5 524,40" stroke="#131c2c" stroke-width="6" fill="none" />
            
            <!-- Connection Pipeline Animated Flow -->
            <path d="M 76,40 Q 300,5 524,40" stroke="url(#pipe-grad)" stroke-width="2.5" fill="none" class="telemetry-dash-pipe" />
            
            <!-- Swarm Engine Node -->
            <circle cx="60" cy="40" r="14" fill="#ff3344" class="telemetry-node-swarm" filter="url(#glow-red)" />
            <text x="60" y="70" fill="#ff3344" font-size="8.5" font-family="monospace" text-anchor="middle" font-weight="bold">SWARM AGENTS</text>
            
            <!-- Arize Phoenix Node -->
            <circle cx="540" cy="40" r="14" fill="#00ffd0" class="telemetry-node-arize" filter="url(#glow-cyan)" />
            <text x="540" y="70" fill="#00ffd0" font-size="8.5" font-family="monospace" text-anchor="middle" font-weight="bold">PHOENIX SAAS</text>
            
            <!-- Flowing Data Signal Packets (Animate Motion) -->
            <circle r="4" fill="#00ffd0" filter="url(#glow-cyan)">
                <animateMotion dur="2.8s" repeatCount="indefinite" path="M 76,40 Q 300,5 524,40" />
            </circle>
            
            <circle r="4" fill="#ff3344" filter="url(#glow-red)">
                <animateMotion dur="2.8s" begin="0.9s" repeatCount="indefinite" path="M 76,40 Q 300,5 524,40" />
            </circle>
            
            <circle r="3.5" fill="#9d4edd" filter="url(#glow-cyan)">
                <animateMotion dur="2.8s" begin="1.8s" repeatCount="indefinite" path="M 76,40 Q 300,5 524,40" />
            </circle>
        </svg>

        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 15px; font-family: monospace; font-size: 0.72em;">
            <div style="background: #0f1520; padding: 8px; border-radius: 4px; border: 1px solid #1a2538;">
                <div style="color: #5a6f82; font-weight: bold; margin-bottom: 2px;">COLLECTOR TYPE</div>
                <div style="color: #eceff1; font-weight: bold;">{collector_type}</div>
            </div>
            <div style="background: #0f1520; padding: 8px; border-radius: 4px; border: 1px solid #1a2538;">
                <div style="color: #5a6f82; font-weight: bold; margin-bottom: 2px;">INGEST STATUS</div>
                <div style="color: {status_color}; font-weight: bold;">{status_text}</div>
            </div>
            <div style="background: #0f1520; padding: 8px; border-radius: 4px; border: 1px solid #1a2538;">
                <div style="color: #5a6f82; font-weight: bold; margin-bottom: 2px;">TRACES EXPORTED</div>
                <div style="color: #eceff1; font-weight: bold;">{total_traces} active</div>
            </div>
            <div style="background: #0f1520; padding: 8px; border-radius: 4px; border: 1px solid #1a2538;">
                <div style="color: #5a6f82; font-weight: bold; margin-bottom: 2px;">TOTAL SPANS</div>
                <div style="color: #eceff1; font-weight: bold;">{total_spans} records</div>
            </div>
        </div>
        <div style="margin-top: 10px; font-family: monospace; font-size: 0.68em; color: #5a6f82; word-break: break-all; border-top: 1px solid #162030; padding-top: 8px;">
            <strong>ACTIVE OTLP ENDPOINT:</strong> {endpoint_url}
        </div>
    </div>
    """
    st.markdown(clean_html(svg_html), unsafe_allow_html=True)

    if not GLOBAL_TRACE_CONSOLE:
        st.info("Awaiting execution traces. Launch doomsday intelligence scan to record active traces.")
        return
        
    for trace in GLOBAL_TRACE_CONSOLE[::-1]:  # Show latest traces first
        with st.expander(f"🛰️ Trace: {trace['name']} | Ticker: {trace['ticker']} | Duration: {trace['duration_ms']}ms", expanded=False):
            st.markdown(clean_html(f"""
            <div style="background-color:#101622; border-left:4px solid #00ffd0; padding:10px; margin-bottom:10px; border-radius:4px; font-family:monospace; font-size:0.85em">
                <strong style="color: #ffffff;">Trace ID:</strong> <span style="color: #ffffff; font-weight: bold;">{trace['trace_id']}</span><br>
                <strong style="color: #ffffff;">Start Time:</strong> <span style="color: #ffffff; font-weight: bold;">{trace['start_time']}</span><br>
                <strong style="color: #ffffff;">Status:</strong> <span style="color:#00ffd0; font-weight: bold;">{trace['status']}</span>
            </div>
            """), unsafe_allow_html=True)
            
            for span in trace['spans']:
                status_color = "#00ffd0" if span['status'] == "SUCCESS" else "#ff1744"
                st.markdown(clean_html(f"""
                <div style="background-color:#161f30; padding:10px; margin-left:20px; margin-bottom:8px; border-radius:4px; border-left:3px solid #00ffd0">
                    <div style="display:flex; justify-content:space-between; font-size:0.85em;">
                        <strong style="color:#00ffd0">Span: {span['name']}</strong>
                        <span style="color:#ffffff; font-family:monospace; font-weight: bold;">
                            {span['duration_ms']}ms | <span style="color:{status_color}; font-weight: bold;">{span['status']}</span>
                        </span>
                    </div>
                </div>
                """), unsafe_allow_html=True)
                
                # Show inputs/outputs in columns if they exist
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("<div style='margin-left: 20px; margin-bottom: 6px;'><strong style='color:#ffffff; font-size:0.85em;'>Span Inputs</strong></div>", unsafe_allow_html=True)
                    formatted_inputs = format_telemetry_dict(span.get("inputs", {}))
                    st.markdown(clean_html(f"""
                    <div style="background: #0c1018; border: 1px solid #1a2538; border-radius: 6px; padding: 12px; margin-left: 20px; margin-right: 0px;">
                        {formatted_inputs}
                    </div>
                    """), unsafe_allow_html=True)
                with c2:
                    st.markdown("<div style='margin-left: 20px; margin-bottom: 6px;'><strong style='color:#ffffff; font-size:0.85em;'>Span Outputs</strong></div>", unsafe_allow_html=True)
                    formatted_outputs = format_telemetry_dict(span.get("outputs", {}))
                    st.markdown(clean_html(f"""
                    <div style="background: #0c1018; border: 1px solid #1a2538; border-radius: 6px; padding: 12px; margin-left: 20px; margin-right: 0px;">
                        {formatted_outputs}
                    </div>
                    """), unsafe_allow_html=True)
                    
                if span.get("metadata"):
                    formatted_metadata = format_telemetry_dict(span['metadata'])
                    st.markdown(clean_html(f"""
                    <div style="margin-left: 20px; margin-top: 8px; margin-bottom: 12px; padding: 12px; background: #070a0e; border: 1px solid #141c28; border-radius: 4px;">
                        <span style="color: #5a6f82; font-size: 0.8em; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; display: block; margin-bottom: 6px;">Metadata Details</span>
                        {formatted_metadata}
                    </div>
                    """), unsafe_allow_html=True)


# ===============================================================
# MAIN APPLICATION
# ===============================================================


def main():
    """Main app - progressive rendering architecture."""
    
    # Session defaults
    defaults = {
        "done": False, "world_state": None, "company": None,
        "verdicts": [], "nodes": [], "hq": None, "valuation": None,
        "chaos": 0.5, "last_chaos": 0.5, "ticker": "NVDA",
        "terminal_log": []
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    
    # === SIDEBAR ===
    with st.sidebar:
        st.markdown('<div class="section-hdr">RAPID AGENT CONSOLE</div>', unsafe_allow_html=True)
        
        ticker = st.text_input("TARGET", value=st.session_state.ticker, help="US: NVDA, AAPL | India: RELIANCE.NS").strip().upper()
        st.session_state.ticker = ticker
        
        st.markdown('<div style="margin-top:-15px"></div>', unsafe_allow_html=True)
        st.markdown('<div style="border-top:1px solid #1a2538; margin:8px 0"></div>', unsafe_allow_html=True)
        st.markdown('<div class="section-hdr">Chaos Level</div>', unsafe_allow_html=True)
        
        chaos = st.slider("Stress", 0.0, 1.0, st.session_state.chaos, 0.05, label_visibility="collapsed")
        st.session_state.chaos = chaos
        
        # Chaos visual
        chaos_labels = {0.2: ("MILD", "success"), 0.4: ("MODERATE", "info"), 0.6: ("SEVERE", "warning"), 0.8: ("CRISIS", "error"), 1.0: ("DOOMSDAY", "error")}
        for threshold, (label, func_name) in sorted(chaos_labels.items()):
            if chaos <= threshold:
                getattr(st, func_name)(f"{label} [{chaos:.0%}]")
                break
        
        st.markdown('<div style="margin-top:-15px"></div>', unsafe_allow_html=True)
        st.markdown('<div style="border-top:1px solid #1a2538; margin:8px 0"></div>', unsafe_allow_html=True)
        with st.expander("API CONFIG"):
            st.text_input("LLM API Key", placeholder="Google AI Studio, NVIDIA NIM, or Fireworks key", type="password", key="user_llm_key")
            st.text_input("Tavily API Key", placeholder="Get key at tavily.com", type="password", key="user_tavily_key")
            st.text_input("Phoenix API Key (Optional)", placeholder="For Arize Cloud tracing", type="password", key="user_phoenix_key")
            st.text_input("Phoenix Endpoint (Optional)", placeholder="e.g. https://app.phoenix.arize.com/v1/traces", type="password", key="user_phoenix_endpoint")
            st.markdown('<div style="color:#5a6f82; font-family:monospace; font-size:0.65em; margin-top:5px">Keys stay in your browser. Not stored.<br>Get free keys: ai.google.dev | build.nvidia.com | fireworks.ai | tavily.com</div>', unsafe_allow_html=True)
        
        st.markdown('<div style="margin-top:-15px"></div>', unsafe_allow_html=True)
        st.markdown('<div style="border-top:1px solid #1a2538; margin:8px 0"></div>', unsafe_allow_html=True)
        launch = st.button("LAUNCH ANALYSIS", type="primary", use_container_width=True)
        
        # World state in sidebar
        if st.session_state.world_state:
            ws = st.session_state.world_state
            fear_c = {"CALM": "#00e676", "CAUTIOUS": "#ffd600", "ANXIOUS": "#ff6d00", "PANIC": "#ff1744"}.get(ws.fear_level, "#fff")
            st.markdown(f"""
            <div class="info-panel">
                <div class="m-label" style="text-align:left; color:{fear_c}">Global Fear</div>
                <div class="m-val" style="text-align:left; font-size:1.1em; color:{fear_c}">{ws.fear_level}</div>
                <div style="font-size:0.7em; margin-top:8px; color:#5a6f82">
                    VIX: {ws.vix} | Oil: ${ws.oil_brent} | Gold: ${ws.gold}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # === HEADER ===
    ws = st.session_state.world_state
    fear = ws.fear_level if ws else "SCANNING"
    badge_cls = "badge-critical" if fear == "PANIC" else "badge-threat" if fear in ["ANXIOUS", "CAUTIOUS"] else "badge-active"
    
    st.markdown(f"""
    <div class="header-bar">
        <div class="header-title">[!] DOOMSDAY RAPID AGENT</div>
        <div class="header-meta">
            <span class="status-badge badge-active">SWARM ACTIVE</span>
            <span class="status-badge {badge_cls}">THREAT: {fear}</span>
            <span style="margin-left:15px">{datetime.utcnow().strftime("%H:%M:%S UTC")}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # === LAUNCH ===
    if launch:
        apply_user_keys()
        
        # Check if any LLM key is available
        has_llm = bool(os.getenv("GOOGLE_API_KEY") or os.getenv("NVIDIA_API_KEY") or os.getenv("FIREWORKS_API_KEY"))
        has_tavily = bool(os.getenv("TAVILY_API_KEY"))
        
        if not has_llm:
            st.error("No LLM API key found. Enter your key in the sidebar (Google AI Studio, NVIDIA NIM, or Fireworks).")
            st.stop()
            
        log = []
        def add_log(msg, level="info"):
            ts = datetime.utcnow().strftime("%H:%M:%S")
            log.append({"ts": ts, "msg": msg, "level": level})

        if not has_tavily:
            add_log("WARNING: No Tavily key. Using AI-only analysis (no live news search).", "warn")
        
        progress_bar = st.progress(0, text="Initializing...")
        terminal = st.empty()
        
        def render_terminal():
            html = '<div class="terminal-feed">'
            for entry in log[-20:]:
                cls = f"t-{entry['level']}"
                html += f'<div class="t-line"><span class="t-time">[{entry["ts"]}]</span> <span class="{cls}">{entry["msg"]}</span></div>'
            html += '</div>'
            terminal.markdown(html, unsafe_allow_html=True)
        
        # STEP 1: AI Init
        add_log("Initializing AI provider chain...", "info")
        render_terminal()
        
        ai = DoomsdayAI()
        try:
            provider_name = ai.initialize()
            add_log(f"Provider locked: {provider_name}", "ok")
        except Exception as e:
            add_log(f"FATAL: No AI provider available - {e}", "err")
            render_terminal()
            st.stop()
        
        progress_bar.progress(10, text="AI Ready")
        render_terminal()
        
        # STEP 2: World State
        add_log("Fetching world state (VIX, Oil, Gold, Yields)...", "info")
        render_terminal()
        
        world_state = fetch_world_state_data()
        st.session_state.world_state = world_state
        add_log(f"World: VIX={world_state.vix} | Fear={world_state.fear_level} | Oil=${world_state.oil_brent}", "ok")
        
        progress_bar.progress(20, text="World State Loaded")
        render_terminal()
        
        # STEP 3: Company Data
        resolved_ticker = resolve_ticker(ticker)
        if resolved_ticker.upper() != ticker.upper():
            add_log(f"Resolved query '{ticker}' to ticker symbol '{resolved_ticker}'", "ok")
            
        add_log(f"Fetching company data for {resolved_ticker}...", "info")
        render_terminal()
        
        company = fetch_company_data(resolved_ticker)
        if not company:
            add_log(f"FAILED: Could not fetch data for {ticker} (Resolved: {resolved_ticker}). Check ticker.", "err")
            render_terminal()
            st.error(f"Could not fetch data for '{ticker}' (Resolved: '{resolved_ticker}'). Enter a valid company name (e.g. Tesla, Reliance, TSMC, Apple) or ticker symbol.")
            st.stop()
        
        st.session_state.company = company
        add_log(f"Loaded: {company.name} | MCap: ${company.market_cap/1e9:.1f}B | Sector: {company.sector}", "ok")
        
        progress_bar.progress(30, text=f"{company.name} Loaded")
        render_terminal()
        
        # STEP 4: Intelligence Scan
        add_log("Multi-domain intelligence scan (5 vectors)...", "info")
        add_log("  -> Geopolitical | Supply Chain | Financial | Regulatory | Technology", "dim")
        render_terminal()
        
        tavily = get_tavily()
        if not tavily:
            add_log("WARNING: Tavily not available. Using AI-only analysis.", "warn")
        
        risks = run_intelligence_scan(ai, tavily, ticker, company, world_state)
        add_log(f"Intelligence complete: {len(risks)} candidate risks identified", "ok")
        
        progress_bar.progress(50, text="Intelligence Complete")
        render_terminal()
        
        # STEP 5: Adversarial Debate (progressive)
        add_log("Fracture Tribunal initiating...", "info")
        add_log("  -> Bear Advocate | Bull Advocate | Fracture Judge", "dim")
        render_terminal()
        
        verdicts = []
        for idx, risk in enumerate(risks):
            add_log(f"  Debating [{idx+1}/{len(risks)}]: {risk.get('title', '')[:50]}...", "info")
            render_terminal()
            
            verdict = run_debate(ai, ticker, company, risk, world_state)
            if verdict:
                verdicts.append(verdict)
                sev_label = "CRITICAL" if verdict.severity_score >= 8 else "HIGH" if verdict.severity_score >= 6 else "VALIDATED"
                add_log(f"    -> {sev_label} (Severity: {verdict.severity_score:.1f})", "warn" if verdict.severity_score >= 6 else "ok")
            else:
                add_log(f"    -> DISMISSED by Judge", "dim")
            render_terminal()
            
            progress_bar.progress(50 + int((idx + 1) / len(risks) * 25), text=f"Debating {idx+1}/{len(risks)}")
        
        st.session_state.verdicts = verdicts
        add_log(f"Tribunal complete: {len(verdicts)} risks validated, {len(risks) - len(verdicts)} dismissed", "ok")

        # STEP 5b: Contagion Cascade
        add_log("[SWARM] Modeling contagion propagation chains...", "info")
        render_terminal()
        contagion_chains = generate_contagion_chains(ai, company, [v.__dict__ if hasattr(v, '__dict__') else v for v in verdicts], chaos)
        st.session_state['contagion_chains'] = contagion_chains
        add_log(f"Contagion: {len(contagion_chains)} chains modeled", "ok")
        render_terminal()
        render_terminal()
        
        # STEP 6: Geographic Mapping
        add_log("Mapping fracture nodes to coordinates...", "info")
        render_terminal()
        
        hq = get_hq_coords(ticker, company.name, company.city, company.country)
        st.session_state.hq = hq
        nodes = map_risks_to_coords(verdicts)
        st.session_state.nodes = nodes
        add_log(f"Mapped {len(nodes)} nodes | HQ: {hq[2]}", "ok")
        
        progress_bar.progress(85, text="Mapping Complete")
        render_terminal()
        
        # STEP 7: Valuation
        add_log("Computing distressed valuation...", "info")
        render_terminal()
        
        avg_sev = sum(v.severity_score for v in verdicts) / len(verdicts) if verdicts else 5.0
        valuation = compute_valuation(company, chaos, avg_sev)
        st.session_state.valuation = valuation
        st.session_state.last_chaos = chaos
        
        add_log(f"Valuation: Base=${valuation.base_fair_value:.2f} | Distressed=${valuation.distressed_value:.2f} | Downside={valuation.downside_pct:.1f}%", "ok")
        
        progress_bar.progress(100, text="ANALYSIS COMPLETE")
        add_log("=== RAPID AGENT ANALYSIS COMPLETE ===", "ok")
        render_terminal()
        
        st.session_state.done = True
        st.session_state.terminal_log = log
        
        time.sleep(1)
        st.rerun()
    
    # === CHAOS SLIDER LIVE UPDATE ===
    if st.session_state.done and abs(chaos - st.session_state.last_chaos) > 0.01:
        company = st.session_state.company
        verdicts = st.session_state.verdicts
        if company:
            avg_sev = sum(v.severity_score for v in verdicts) / len(verdicts) if verdicts else 5.0
            valuation = compute_valuation(company, chaos, avg_sev)
            st.session_state.valuation = valuation
            st.session_state.last_chaos = chaos
    
    # === RENDER RESULTS ===
    if st.session_state.done:
        val = st.session_state.valuation
        verdicts = st.session_state.verdicts
        nodes = st.session_state.nodes
        hq = st.session_state.hq
        company = st.session_state.company
        
        # METRICS
        n_risks = len(verdicts)
        max_sev = max((v.severity_score for v in verdicts), default=0)
        threat = "CRITICAL" if max_sev >= 8 else "HIGH" if max_sev >= 6 else "ELEVATED" if max_sev >= 4 else "LOW"
        threat_cls = "c-critical" if max_sev >= 8 else "c-orange" if max_sev >= 6 else "c-yellow" if max_sev >= 4 else "c-green"
        ds_cls = "c-red" if val.downside_pct <= -30 else "c-orange" if val.downside_pct <= -15 else "c-yellow"
        
        st.markdown(f"""
        <div class="metrics-grid">
            <div class="m-card"><div class="m-val">${val.current_price:.2f}</div><div class="m-label">Market Price</div></div>
            <div class="m-card"><div class="m-val" style="color:#00e676">${val.base_fair_value:.2f}</div><div class="m-label">Base Fair Value</div></div>
            <div class="m-card"><div class="m-val" style="color:#ff1744">${val.distressed_value:.2f}</div><div class="m-label">Distressed Value</div></div>
            <div class="m-card"><div class="m-val {ds_cls}">{val.downside_pct:.1f}%</div><div class="m-label">Downside Risk</div></div>
            <div class="m-card"><div class="m-val {threat_cls}">{threat}</div><div class="m-label">Threat Level</div></div>
            <div class="m-card"><div class="m-val">{n_risks}</div><div class="m-label">Active Risks</div></div>
        </div>
        """, unsafe_allow_html=True)
        
        # MAP
        st.markdown('<div class="section-hdr">Global Fracture Map -- Vulnerability Network</div>', unsafe_allow_html=True)
        render_map(nodes, hq)
        
        # RISK CARDS (WorldMonitor style)
        st.markdown('<div class="section-hdr">Validated Risk Feed</div>', unsafe_allow_html=True)
        render_risk_cards(verdicts)
        
        # CHARTS
        st.markdown('<div class="section-hdr">Valuation Destruction Waterfall</div>', unsafe_allow_html=True)
        col1, col2 = st.columns([2, 1])
        with col1:
            render_waterfall(val)
        with col2:
            st.markdown(f"""
            <div class="info-panel">
                <div class="section-hdr" style="margin-top:0">Methodology</div>
                <div class="ws-row"><span class="ws-k">Engine</span><span class="ws-v">{val.valuation_method}</span></div>
                <div class="ws-row"><span class="ws-k">Base WACC</span><span class="ws-v">{val.base_wacc:.1f}%</span></div>
                <div class="ws-row"><span class="ws-k">Stressed WACC</span><span class="ws-v" style="color:#ff1744">{val.stressed_wacc:.1f}%</span></div>
                <div class="ws-row"><span class="ws-k">Revenue Haircut</span><span class="ws-v" style="color:#ff1744">{val.revenue_haircut:.1f}%</span></div>
                <div class="ws-row"><span class="ws-k">Margin Compression</span><span class="ws-v" style="color:#ff1744">{val.margin_compression_bps:.0f} bps</span></div>
                <div class="ws-row" style="border:none"><span class="ws-k">Chaos Applied</span><span class="ws-v" style="color:#ff6d00">{chaos:.0%}</span></div>
            </div>
            """, unsafe_allow_html=True)
        
        # DEBATE TRANSCRIPTS
        st.markdown('<div class="section-hdr">Fracture Tribunal -- Adversarial Debate</div>', unsafe_allow_html=True)
        render_debate_feed(verdicts)
        
        # CONTAGION CASCADE
        if st.session_state.get('contagion_chains'):
            render_contagion_section(st.session_state['contagion_chains'], chaos)

        # TERMINAL LOG (collapsible)
        if st.session_state.terminal_log:
            with st.expander("[SWARM LOG] Execution Trace"):
                html = '<div class="terminal-feed" style="max-height:none">'
                for entry in st.session_state.terminal_log:
                    cls = f"t-{entry['level']}"
                    html += f'<div class="t-line"><span class="t-time">[{entry["ts"]}]</span> <span class="{cls}">{entry["msg"]}</span></div>'
                html += '</div>'
                st.markdown(html, unsafe_allow_html=True)
        
        # ARIZE PHOENIX TELEMETRY CONSOLE
        render_arize_telemetry_console()
        
        # VALUATION TRANSPARENCY
        render_valuation_transparency(company, val, chaos, verdicts)

        # IC SUMMARY
        st.markdown('<div class="section-hdr">Investment Committee Summary</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            ds_color = "#ff1744" if val.downside_pct < -15 else "#ff6d00" if val.downside_pct < 0 else "#00e676"
            st.markdown(f"""
            <div class="info-panel">
                <div class="m-val" style="font-size:1.1em">{company.name} ({ticker})</div>
                <div class="ws-row"><span class="ws-k">Sector</span><span class="ws-v">{company.sector}</span></div>
                <div class="ws-row"><span class="ws-k">Market Cap</span><span class="ws-v">${company.market_cap/1e9:.1f}B</span></div>
                <div class="ws-row"><span class="ws-k">Revenue</span><span class="ws-v">${company.revenue/1e9:.1f}B</span></div>
                <div class="ws-row"><span class="ws-k">Current Price</span><span class="ws-v">${val.current_price:.2f}</span></div>
                <div class="ws-row"><span class="ws-k">Fair Value</span><span class="ws-v" style="color:#00e676">${val.base_fair_value:.2f}</span></div>
                <div class="ws-row"><span class="ws-k">Distressed</span><span class="ws-v" style="color:#ff1744">${val.distressed_value:.2f}</span></div>
                <div class="ws-row" style="border:none"><span class="ws-k">Downside Risk</span><span class="ws-v" style="color:{ds_color}">{val.downside_pct:.1f}%</span></div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            if verdicts:
                risks_html = ""
                for v in sorted(verdicts, key=lambda x: x.severity_score, reverse=True)[:5]:
                    c = "#ff1744" if v.severity_score >= 7 else "#ff6d00" if v.severity_score >= 5 else "#ffd600"
                    risks_html += f'<div class="ws-row" style="font-size:0.85em"><span class="ws-v" style="color:{c}; margin-right:8px">[{v.severity_score:.1f}]</span><span class="ws-k" style="color:#eceff1">{v.risk_description[:70]}...</span></div>'
                st.markdown(f"""
                <div class="info-panel">
                    <div class="m-label" style="text-align:left; margin-bottom:10px">Top Validated Risks</div>
                    {risks_html}
                </div>
                """, unsafe_allow_html=True)
    
    else:
        # === LANDING ===
        st.markdown("""
        <div class="landing-box">
            <div class="landing-title">[!] AWAITING TARGET</div>
            <div class="landing-sub">
                Enter a ticker in the sidebar and launch analysis.<br>
                The Doomsday Swarm will scan 5 intelligence domains, run adversarial AI debates,
                map geographic vulnerabilities, and compute distressed valuations.
            </div>
            <div class="metrics-grid" style="max-width:600px; margin:40px auto 0 auto">
                <div class="m-card"><div class="m-val" style="font-size:1.1em; color:#5a6f82">01</div><div class="m-label">Intel</div></div>
                <div class="m-card"><div class="m-val" style="font-size:1.1em; color:#5a6f82">02</div><div class="m-label">Debate</div></div>
                <div class="m-card"><div class="m-val" style="font-size:1.1em; color:#5a6f82">03</div><div class="m-label">Map</div></div>
                <div class="m-card"><div class="m-val" style="font-size:1.1em; color:#5a6f82">04</div><div class="m-label">Value</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()