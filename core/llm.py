import json
import os
import threading
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# Pehla model main hai, baaki backup. Ek fail ho toh agla try hota hai.
MODELS = [
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
]

TIMEOUT_SECONDS = 45
ROUNDS = 2


class LLMError(Exception):
    """Sab models fail ho gaye ya key missing hai."""


_client = None


def _get_client():
    global _client
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise LLMError("GEMINI_API_KEY nahi mili. .env file check karo.")
    if _client is None:
        _client = genai.Client(
            api_key=key,
            http_options=types.HttpOptions(timeout=TIMEOUT_SECONDS * 1000),
        )
    return _client


def _run_with_timeout(fn, seconds):
    """fn ko alag thread me chalata hai. Time se zyada lage toh chhod deta hai."""
    box = {}

    def worker():
        try:
            box["value"] = fn()
        except Exception as e:
            box["error"] = e

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    t.join(seconds)
    if t.is_alive():
        raise TimeoutError(f"{seconds} second me jawab nahi aaya")
    if "error" in box:
        raise box["error"]
    return box["value"]


def generate(prompt, system=None, json_mode=False, temperature=0.2):
    """Text lautata hai: (text, model_ka_naam)."""
    client = _get_client()
    config = types.GenerateContentConfig(
        system_instruction=system,
        temperature=temperature,
        response_mime_type="application/json" if json_mode else None,
    )

    last_error = None
    for round_no in range(ROUNDS):
        for model in MODELS:
            try:
                resp = _run_with_timeout(
                    lambda m=model: client.models.generate_content(
                        model=m, contents=prompt, config=config
                    ),
                    TIMEOUT_SECONDS + 5,
                )
                text = resp.text
                if not text:
                    raise ValueError("Khali jawab aaya")
                return text, model
            except Exception as e:
                last_error = e
        if round_no < ROUNDS - 1:
            time.sleep(2)

    raise LLMError(f"Sab models fail ho gaye. Last error: {str(last_error)[:200]}")


def _clean_json_text(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    return text.strip()


def generate_json(prompt, system=None):
    """JSON lautata hai: (python_data, model_ka_naam)."""
    text, model = generate(prompt, system=system, json_mode=True)
    try:
        return json.loads(_clean_json_text(text)), model
    except json.JSONDecodeError:
        text, model = generate(
            prompt + "\n\nReturn ONLY valid JSON. No extra text.",
            system=system,
            json_mode=True,
            temperature=0,
        )
        try:
            return json.loads(_clean_json_text(text)), model
        except json.JSONDecodeError as e:
            raise LLMError(f"Model ne valid JSON nahi diya: {e}")