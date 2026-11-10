"""LLM integration: Gemini (Google AI Studio free tier) + OpenAI, both OPTIONAL.
No key -> deterministic/template mode. Never calls a paid API. Quota-capped,
cached, and any failure falls back to template mode and is logged."""
import json, os, urllib.request, urllib.error
from . import db

DEFAULT_DAILY_CAP = 50

def provider_status():
    gemini = bool(os.environ.get("GEMINI_API_KEY"))
    openai = bool(os.environ.get("OPENAI_API_KEY"))
    mode = "gemini" if gemini else ("openai" if openai else "template")
    return {"mode": mode, "gemini_configured": gemini, "openai_configured": openai,
            "daily_cap": int(db.get_setting("llm_daily_cap", DEFAULT_DAILY_CAP) or DEFAULT_DAILY_CAP),
            "calls_today": calls_today(),
            "note": "Template mode: deterministic built-in generators. No paid API is ever called."}

def _today():
    from datetime import date
    return date.today().isoformat()

def calls_today():
    c = db.connect()
    r = c.execute("SELECT COALESCE(SUM(calls),0) s FROM llm_usage WHERE day=?", (_today(),)).fetchone()
    c.close()
    return int(r["s"])

def _record_call(provider, model):
    c = db.connect()
    c.execute("INSERT INTO llm_usage(provider,model,calls,day,created_at) VALUES(?,?,?,?,?)",
              (provider, model, 1, _today(), db.now()))
    c.commit(); c.close()

def _cap_reached():
    return calls_today() >= int(db.get_setting("llm_daily_cap", DEFAULT_DAILY_CAP) or DEFAULT_DAILY_CAP)

def generate(prompt, task="general"):
    """Returns (text_or_None, source). source in {'gemini','openai','template','failed'}.
    Never raises: failures return (None, 'failed') and are logged."""
    if _cap_reached():
        db.log_error("llm", "Daily LLM cap reached; falling back to template mode.")
        return None, "template"
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}"
            body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode()
            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            _record_call("gemini", "gemini-2.0-flash")
            return text, "gemini"
        except Exception as e:  # noqa: BLE001 - fallback by design
            db.log_error("llm", f"Gemini call failed ({type(e).__name__}): {e}; falling back to template mode.")
            return None, "failed"
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        try:
            body = json.dumps({"model": "gpt-4o-mini",
                               "messages": [{"role": "user", "content": prompt}]}).encode()
            req = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=body,
                                         headers={"Content-Type": "application/json",
                                                  "Authorization": f"Bearer {key}"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
            text = data["choices"][0]["message"]["content"]
            _record_call("openai", "gpt-4o-mini")
            return text, "openai"
        except Exception as e:  # noqa: BLE001
            db.log_error("llm", f"OpenAI call failed ({type(e).__name__}): {e}; falling back to template mode.")
            return None, "failed"
    return None, "template"
