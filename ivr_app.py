# Root shim used by Render ("Serving Flask app 'ivr_app'")
from typing import Any, Dict

try:
    # Try to import your real app + helpers
    from services.ivr.ivr_app import app as real_app, get_client_info, speak  # type: ignore
except Exception as e:
    # Fallback: minimal app so service still boots
    print("=== SHIM: could not import services.ivr.ivr_app, using fallback ===", e)
    from flask import Flask
    def get_client_info(number: str) -> Dict[str, Any]: return {}
    def speak(vr, text: str, client_info: Dict[str, Any]): vr.say(text)
    real_app = Flask(__name__)

# The app object Render actually runs
app = real_app

# --- Views we will register programmatically ---
from flask import request, jsonify
from twilio.twiml.voice_response import VoiceResponse

def _shim_ok():
    try:
        routes = sorted([r.rule for r in app.url_map.iter_rules()])
    except Exception:
        routes = []
    return jsonify({"ok": True, "source": "root shim", "routes": routes})

def _say_hours():
    called = request.args.get("called", "+18579579141")
    info = get_client_info(called)
    hours = (info or {}).get("business_hours")
    vr = VoiceResponse()
    if hours:
        speak(vr, f"Our business hours are {hours}.", info)
    else:
        speak(vr, "Sorry, I don’t have our business hours on file.", info)
    return str(vr)

# --- Register routes explicitly (no decorators) ---
app.add_url_rule("/admin/shim-ok", "shim_ok", _shim_ok, methods=["GET"])
app.add_url_rule("/admin/say-hours", "say_hours", _say_hours, methods=["GET"])

# Print the route map so we can see it in Render logs at import time
try:
    print("=== SHIM: routes now ===", sorted([r.rule for r in app.url_map.iter_rules()]))
except Exception as e:
    print("=== SHIM: could not print routes ===", e)
