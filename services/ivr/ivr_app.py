from flask import Flask, request, Response, jsonify
import os, json, traceback, sys

app = Flask(__name__)

def _xml(body:str, code:int=200):
    return Response(body, status=code, mimetype="text/xml")

def _twiml_say(msg:str):
    return f'<?xml version="1.0" encoding="UTF-8"?><Response><Say>{msg}</Say><Hangup/></Response>'

def load_hours():
    env_hours = os.getenv("BUSINESS_HOURS_JSON")
    if env_hours:
        try:
            return json.loads(env_hours)
        except Exception:
            pass
    for candidate in ("hours.json", "config/hours.json", "services/ivr/hours.json"):
        if os.path.exists(candidate):
            with open(candidate, "r", encoding="utf-8") as f:
                return json.load(f)
    return {
        "timezone": "America/New_York",
        "mon": "9:00-17:00",
        "tue": "9:00-17:00",
        "wed": "9:00-17:00",
        "thu": "9:00-17:00",
        "fri": "9:00-17:00",
        "sat": "closed",
        "sun": "closed"
    }

def hours_sentence(h):
    keys = ["mon","tue","wed","thu","fri","sat","sun"]
    parts = []
    names = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    for k,nm in zip(keys,names):
        val = h.get(k, "closed")
        parts.append(f"{nm} {val}")
    return ", ".join(parts)

@app.get("/")
def root():
    return "Autonomy IVR is up", 200

@app.get("/admin/shim-ok")
def shim_ok():
    return "OK", 200

@app.get("/admin/say-hours")
def say_hours():
    return jsonify(load_hours()), 200

# Twilio-safe error handler: always return valid TwiML + 200
@app.errorhandler(Exception)
def handle_error(e):
    traceback.print_exc(file=sys.stderr)
    msg = "Sorry, our system hit a snag. Please call back shortly."
    return _xml(_twiml_say(msg), 200)

# Simple TwiML sanity check endpoint
@app.route("/twilio/ping", methods=["GET","POST"])
def twilio_ping():
    return _xml(_twiml_say("Autonomy IVR is online."), 200)

# Voice webhook (accept GET just in case)
@app.route("/voice", methods=["POST","GET"])
def voice():
    h = load_hours()
    brief = hours_sentence(h)
    # Relative action URL is fine; Twilio resolves it against the webhook URL
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather input="dtmf" numDigits="1" action="/voice/menu" method="POST" timeout="5">
    <Say>Welcome to Autonomy Receptionist. Press 1 to hear our business hours.</Say>
  </Gather>
  <Say>No input received. {brief}</Say>
  <Hangup/>
</Response>"""
    return _xml(twiml, 200)

@app.route("/voice/menu", methods=["POST","GET"])
def voice_menu():
    digit = (request.values.get("Digits") or "").strip()
    if digit == "1":
        brief = hours_sentence(load_hours())
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Our hours are: {brief}</Say>
  <Hangup/>
</Response>"""
    else:
        twiml = """<?xml version="1.0" encoding="UTF-8"?><Response><Say>Invalid selection. Goodbye.</Say><Hangup/></Response>"""
    return _xml(twiml, 200)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
