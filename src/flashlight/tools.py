"""Real tools available to agents.

Every tool here performs a genuine operation — a live HTTP request to a
public data source, or real local Whisper inference. On failure a tool
returns a structured error for the model to relay; it never fabricates
a substitute result.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import requests

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
STOOQ_URL = "https://stooq.com/q/l/"


def get_crypto_price(coin_ids: str, vs_currency: str = "usd") -> str:
    """Fetch live prices from the CoinGecko public API (no key required)."""
    ids = ",".join(part.strip().lower() for part in coin_ids.split(",") if part.strip())
    if not ids:
        return json.dumps({"error": "No coin ids given. Example: 'bitcoin,ethereum'."})
    try:
        resp = requests.get(
            COINGECKO_URL,
            params={
                "ids": ids,
                "vs_currencies": vs_currency.lower(),
                "include_market_cap": "true",
                "include_24hr_change": "true",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        return json.dumps(
            {"error": f"Live price lookup failed: {exc}. Do not guess a price."}
        )
    if not data:
        return json.dumps(
            {"error": f"CoinGecko returned no data for ids: {ids}. "
                      "Check the coin id (e.g. 'bitcoin', not 'BTC')."}
        )
    return json.dumps(
        {
            "source": "CoinGecko live API",
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
            "prices": data,
        }
    )


def get_stock_quote(symbols: str) -> str:
    """Fetch recent stock quotes from Stooq's free CSV endpoint.

    US tickers need a `.us` suffix (e.g. aapl.us); this is added
    automatically when no suffix is present.
    """
    cleaned = []
    for part in symbols.split(","):
        sym = part.strip().lower()
        if not sym:
            continue
        if "." not in sym:
            sym += ".us"
        cleaned.append(sym)
    if not cleaned:
        return json.dumps({"error": "No symbols given. Example: 'AAPL,MSFT'."})
    try:
        resp = requests.get(
            STOOQ_URL,
            params={"s": ",".join(cleaned), "f": "sd2t2ohlcv", "h": "", "e": "csv"},
            timeout=15,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        return json.dumps(
            {"error": f"Live quote lookup failed: {exc}. Do not guess a quote."}
        )

    lines = resp.text.strip().splitlines()
    if len(lines) < 2:
        return json.dumps({"error": f"Stooq returned no rows for: {symbols}"})
    header = [h.strip().lower() for h in lines[0].split(",")]
    quotes = []
    for line in lines[1:]:
        row = dict(zip(header, [c.strip() for c in line.split(",")]))
        if row.get("close") in ("N/D", "", None):
            quotes.append({"symbol": row.get("symbol"), "error": "no data (check symbol)"})
        else:
            quotes.append(row)
    return json.dumps(
        {
            "source": "Stooq live CSV API",
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
            "quotes": quotes,
        }
    )


def transcribe_audio(file_path: str, language: str | None = None) -> str:
    """Transcribe a local audio file with faster-whisper (real inference)."""
    path = Path(file_path).expanduser()
    if not path.is_file():
        return json.dumps(
            {"error": f"Audio file not found: {path}. "
                      "Provide the full path to a real file."}
        )
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return json.dumps(
            {"error": "faster-whisper is not installed. Install real "
                      "transcription support with: pip install 'flashlight[media]' "
                      "(or pip install faster-whisper). No transcript can be "
                      "produced without it."}
        )
    try:
        model = WhisperModel("base", device="auto", compute_type="auto")
        segments, info = model.transcribe(
            str(path), language=language or None
        )
        text_parts = []
        segment_list = []
        for seg in segments:
            text_parts.append(seg.text.strip())
            segment_list.append(
                {"start": round(seg.start, 2), "end": round(seg.end, 2),
                 "text": seg.text.strip()}
            )
        return json.dumps(
            {
                "source": f"faster-whisper (local), file: {path.name}",
                "detected_language": info.language,
                "duration_seconds": round(info.duration, 2),
                "transcript": " ".join(text_parts),
                "segments": segment_list,
            }
        )
    except Exception as exc:  # transcription backends raise many types
        return json.dumps({"error": f"Transcription failed: {exc}"})


# --- Tool schemas exposed to Ollama's tool-calling API -----------------

TOOL_SCHEMAS: dict[str, dict] = {
    "get_crypto_price": {
        "type": "function",
        "function": {
            "name": "get_crypto_price",
            "description": "Get live cryptocurrency prices, market cap and "
                           "24h change from CoinGecko. Use CoinGecko ids "
                           "such as 'bitcoin', 'ethereum', 'solana'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "coin_ids": {
                        "type": "string",
                        "description": "Comma-separated CoinGecko coin ids",
                    },
                    "vs_currency": {
                        "type": "string",
                        "description": "Quote currency (default 'usd')",
                    },
                },
                "required": ["coin_ids"],
            },
        },
    },
    "get_stock_quote": {
        "type": "function",
        "function": {
            "name": "get_stock_quote",
            "description": "Get recent stock quotes (open/high/low/close/"
                           "volume) from Stooq. Pass ticker symbols like "
                           "'AAPL' or 'MSFT'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbols": {
                        "type": "string",
                        "description": "Comma-separated ticker symbols",
                    },
                },
                "required": ["symbols"],
            },
        },
    },
    "transcribe_audio": {
        "type": "function",
        "function": {
            "name": "transcribe_audio",
            "description": "Transcribe a local audio file using Whisper "
                           "running on this machine. Returns the real "
                           "transcript with timestamps.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the local audio file",
                    },
                    "language": {
                        "type": "string",
                        "description": "Optional ISO language code hint "
                                       "(e.g. 'en'); auto-detected if omitted",
                    },
                },
                "required": ["file_path"],
            },
        },
    },
}

TOOL_FUNCTIONS = {
    "get_crypto_price": get_crypto_price,
    "get_stock_quote": get_stock_quote,
    "transcribe_audio": transcribe_audio,
}


def execute_tool(name: str, arguments: dict) -> str:
    fn = TOOL_FUNCTIONS.get(name)
    if fn is None:
        return json.dumps({"error": f"Unknown tool: {name}"})
    try:
        return fn(**arguments)
    except TypeError as exc:
        return json.dumps({"error": f"Bad arguments for {name}: {exc}"})
