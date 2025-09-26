from flask import Flask, request, Response, jsonify
import os, json, traceback, sys, re

app = Flask(__name__)

def _xml(s):  # always TwiML + 200
    return Response(s, status=200, mimetype="text/xml")

def load_hours():
    env = os.getenv("BUSINESS_HOURS_JSON")
    if env:
        try: return json.loads(env)
        except Exception: pass
    for p in ("services/ivr/hours.json","hours.json","config/hours.json"):
        if os.path.exists(p):
            with open(p,"r",encoding="utf-8") as f: return json.load(f)
    return {"timezone":"America/New_York","mon":"9:00AM-5:00PM","tue":"9:00AM-5:00PM","wed":"9:00AM-5:00PM","thu":"9:00AM-5:00PM","fri":"9:00AM-5:00PM","sat":"Closed","sun":"Closed"}

def hours_sentence(h):
    order=[("mon","Mon"),("tue","Tue"),("wed","Wed"),("thu","Thu"),("fri","Fri"),("sat","Sat"),("sun","Sun")]
    return ", ".join(f"{nm} {h.get(k,'Closed')}" for k,nm in order)

def route_intent(text):
    t=(text or "").lower()
    if any(k in t for k in ["hour","open","close","closing","time"]): return "hours"
    if any(k in t for k in ["price","pricing","cost","plan","subscription"]): return "pricing"
    if any(k in t for k in ["location","address","where","directions"]): return "location"
    if any(k in t for k in ["operator","human","agent","representative","someone"]): return "operator"
    if any(k in t for k in ["repeat","again"]): return "repeat"
    return "unknown"

def get_forward_number():
    """Return E.164 +NNNN… from FORWARD_NUMBER env; accept raw digits like 7815551234."""
    num = (os.getenv("FORWARD_NUMBER") or "").strip()
    if not num:
        return ""
    digits = re.sub(r"\D+", "", num)
    if not digits:
        return ""
    # If already starts w/ country code (e.g., 1 for US), keep it; else assume US
    if digits.startswith("1") and len(digits) == 11:
        return f"+{digits}"
    if not digits.startswith("1") and len(digits) == 10:
        return f"+1{digits}"
    # If user pasted full +… keep it
    if num.startswith("+"):
        return num
    # Fallback: try as-is with +
    return f"+{digits}"

@app.route("/", methods=["GET","POST"])
def root(): return "Autonomy IVR up", 200

@app.get("/admin/say-hours")
def say_hours(): return jsonify(load_hours()), 200

@app.route("/twilio/ping", methods=["GET","POST"])
def ping():
    return _xml("""<?xml version="1.0" encoding="UTF-8"?>
<Response><Say>Autonomy IVR is online.</Say><Redirect>/voice</Redirect></Response>""")

# Global: never crash Twilio; apologize + loop to menu
@app.errorhandler(Exception)
def on_error(e):
    traceback.print_exc(file=sys.stderr)
    return _xml("""<?xml version="1.0" encoding="UTF-8"?>
<Response><Say>Sorry, we hit a snag.</Say><Pause length="1"/><Redirect>/voice</Redirect></Response>""")

def menu_twiml():
    prompt = ("Welcome to Autonomy Receptionist. "
              "You can say things like, what are your hours, pricing, or location. "
              "Or press 1 for hours, 2 for pricing, 3 for location, or 0 for an operator.")
    hints = "hours, pricing, location, operator, human, speak to a person, address"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather input="speech" action="/voice/route" method="POST"
          language="en-US" hints="{hints}" timeout="6" speechTimeout="auto">
    <Say>Welcome to Autonomy Receptionist. You can say things like, what are your hours, pricing, or location.</Say>
  </Gather>
  <Say>No input received.</Say>
  <Redirect>/voice</Redirect>
</Response>"""

@app.route("/voice", methods=["POST","GET"])
def voice():
    return _xml(menu_twiml())

@app.route("/voice/transfer-result", methods=["POST","GET"])
def transfer_result():
    status = (request.values.get("DialCallStatus") or "").lower()
    if status in ("completed","answered"):
        return _xml("""<?xml version="1.0" encoding="UTF-8"?><Response>
  <Say>Thanks for speaking with us.</Say>
  <Pause length="1"/><Say>Anything else?</Say>
  <Redirect>/voice</Redirect>
</Response>""")
    else:
        return _xml("""<?xml version="1.0" encoding="UTF-8"?><Response>
  <Say>Sorry, we couldn't complete the transfer.</Say>
  <Pause length="1"/><Say>Please leave a short message after the tone.</Say>
  <Record maxLength="90" playBeep="true" action="/voice/voicemail-done" method="POST"/>
</Response>""")

@app.route("/voice/voicemail-done", methods=["POST","GET"])
def voicemail_done():
    return _xml("""<?xml version="1.0" encoding="UTF-8"?><Response>
  <Say>Thanks, we received your message.</Say>
  <Pause length="1"/><Say>Would you like anything else?</Say>
  <Redirect>/voice</Redirect>
</Response>""")

# --- Override: richer speech intent routing (human/voicemail synonyms) ---
def route_intent(text):
    t = (text or "").lower().strip()
    synonyms_operator = [
        "operator","human","agent","representative","someone","real person","live person",
        "talk to a human","talk to someone","speak to a human","speak to someone",
        "patch me through","transfer me","connect me","customer service","support",
        "talk to a person","put me through","get me a human"
    ]
    synonyms_voicemail = [
        "leave a message","voicemail","voice mail","record a message","leave voicemail",
        "i want to leave a message","can i leave a message"
    ]
    if any(k in t for k in ["hour","open","close","closing","time","business hours"]): return "hours"
    if any(k in t for k in ["price","pricing","cost","plan","subscription"]): return "pricing"
    if any(k in t for k in ["location","address","where","directions"]): return "location"
    if any(k in t for k in synonyms_voicemail): return "voicemail"
    if any(k in t for k in synonyms_operator): return "operator"
    if any(k in t for k in ["repeat","again","menu","options"]): return "repeat"
    return "unknown"

# --- Whisper to your cell before bridge (press 1 to accept) ---
@app.route("/voice/screen", methods=["GET","POST"])
def screen():
    d = (request.values.get("Digits") or "").strip()
    if d == "1":
        return _xml("""<?xml version="1.0" encoding="UTF-8"?><Response>
  <Say>Connecting.</Say>
</Response>""")
    return _xml("""<?xml version="1.0" encoding="UTF-8"?><Response>
  <Gather numDigits="1" action="/voice/screen" method="POST" timeout="8">
    <Say>Autonomy demo call. Press 1 to accept.</Say>
  </Gather>
  <Say>No input. Goodbye.</Say>
  <Hangup/>
</Response>""")

# --- SMS helper screens: offer to text the info and send it on consent ---
from urllib.parse import quote, unquote, unquote

def _hours_text():
    h = load_hours()
    parts = [f"Mon {h.get('mon','')}", f"Tue {h.get('tue','')}", f"Wed {h.get('wed','')}",
             f"Thu {h.get('thu','')}", f"Fri {h.get('fri','')}", f"Sat {h.get('sat','')}", f"Sun {h.get('sun','')}"]
    return "Autonomy Receptionist — Hours: " + "; ".join(parts)

def _pricing_text():
    return "Autonomy Receptionist — Pricing: $200/mo Starter, $300/mo Pro. Details: autonomy-ai.com"

def _location_text():
    return "Autonomy Receptionist — We operate virtually and support clients anywhere. Info: autonomy-ai.com"

@app.route("/voice/sms-offer", methods=["POST","GET"])
def sms_offer():
    include = (request.args.get("include") or "hours").lower()
    # Build the body now and pass it along (URL-encoded) to the consent handler
    if include == "pricing":
        body = _pricing_text()
    elif include == "location":
        body = _location_text()
    else:
        body = _hours_text()
        include = "hours"

    enc = quote(body)
    return _xml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather input="speech" action="/voice/sms-consent?include={include}&body={enc}" method="POST"
          language="en-US" timeout="6" speechTimeout="auto">
    <Say>Would you like that sent by text? Say yes to receive a text, or say no to skip.</Say>
  </Gather>
  <Say>No input received.</Say>
  <Redirect>/voice</Redirect>
</Response>""")

@app.route("/voice/sms-consent", methods=["POST","GET"])
def sms_consent():
    speech = (request.values.get("SpeechResult") or "").lower().strip()
    include = (request.args.get("include") or "hours").lower()
    body = _unquote(request.args.get("body") or "Autonomy Receptionist")
    said_yes = any(k in speech for k in ["yes","yeah","yep","sure","please","ok","okay","text me","send it"])
    if said_yes and body:
        return _xml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Sms>{body}</Sms>
  <Say>Sent. Anything else?</Say>
  <Redirect>/voice</Redirect>
</Response>""")
    return _xml("""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>No problem. Anything else?</Say>
  <Redirect>/voice</Redirect>
</Response>""")
