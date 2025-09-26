from flask import Flask, request, Response, jsonify
import os, json, traceback, sys
app = Flask(__name__)

def _xml(s): return Response(s, status=200, mimetype="text/xml")
def _say(msg): return f'<?xml version="1.0" encoding="UTF-8"?><Response><Say>{msg}</Say><Hangup/></Response>'

def load_hours():
    env = os.getenv("BUSINESS_HOURS_JSON")
    if env:
        try: return json.loads(env)
        except Exception: pass
    for p in ("services/ivr/hours.json","hours.json","config/hours.json"):
        if os.path.exists(p):
            with open(p,"r",encoding="utf-8") as f: return json.load(f)
    return {"timezone":"America/New_York","mon":"9:00-17:00","tue":"9:00-17:00","wed":"9:00-17:00","thu":"9:00-17:00","fri":"9:00-17:00","sat":"closed","sun":"closed"}

def hours_sentence(h):
    order=[("mon","Mon"),("tue","Tue"),("wed","Wed"),("thu","Thu"),("fri","Fri"),("sat","Sat"),("sun","Sun")]
    return ", ".join(f"{nm} {h.get(k,'closed')}" for k,nm in order)

@app.route("/", methods=["GET","POST"])
def root(): return "Autonomy IVR up", 200

@app.get("/admin/say-hours")
def say_hours(): return jsonify(load_hours()), 200
@app.route("/twilio/ping", methods=["GET","POST"])
def ping(): return _xml(_say("Autonomy IVR is online."))

@app.errorhandler(Exception)
def on_error(e):
    traceback.print_exc(file=sys.stderr)
    return _xml(_say("Sorry, we hit a snag. Please call back shortly."))

@app.route("/voice", methods=["POST","GET"])
def voice():
    brief = hours_sentence(load_hours())
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather input="dtmf" numDigits="1" action="https://autonomy-ivr.onrender.com/voice/menu" method="POST" timeout="6">
    <Say>Welcome to Autonomy Receptionist. Press 1 to hear our business hours.</Say>
  </Gather>
  <Say>No input received. {brief}</Say>
  <Hangup/>
</Response>"""
    return _xml(twiml)
@app.route("/voice/menu", methods=["POST","GET"])
def voice_menu():
    digit = (request.values.get("Digits") or "").strip()
    if digit == "1":
        return _xml(_say(f"Our hours are: {hours_sentence(load_hours())}"))
    return _xml(_say("Invalid selection. Goodbye."))

if __name__ == "__main__":
    port = int(os.getenv("PORT","10000"))
    app.run(host="0.0.0.0", port=port)

# --- Absolute URL builder for Twilio callbacks ---
from urllib.parse import urljoin
def _abs_url(path):
    base = os.getenv("PUBLIC_BASE_URL") or (request.url_root if request else "")
    return urljoin(base, path.lstrip("/"))
