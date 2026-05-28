from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.valuation_engine import DEFAULT_ASSUMPTIONS, compute_valuation

load_dotenv(ROOT / ".env")


def _json_response(handler: BaseHTTPRequestHandler, payload: dict, status: int = 200) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0") or "0")
    raw = handler.rfile.read(length).decode("utf-8") if length else "{}"
    return json.loads(raw or "{}")


def handle(payload: dict[str, Any]) -> dict:
    ticker = str(payload.get("ticker") or "NVDA").upper()
    assumptions = payload.get("assumptions") if isinstance(payload.get("assumptions"), dict) else DEFAULT_ASSUMPTIONS
    return compute_valuation(ticker, assumptions)


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self) -> None:
        _json_response(self, {"ok": True})

    def do_POST(self) -> None:
        try:
            _json_response(self, handle(_read_json(self)))
        except Exception:
            _json_response(self, compute_valuation("NVDA", DEFAULT_ASSUMPTIONS), 200)
