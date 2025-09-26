from flask import Flask, request, Response, jsonify
import os, json, re, traceback, sys
from urllib.parse import quote, unquote

app = Flask(__name__)
def _xml(s): return Response(s, status=200, mimetype="text/xml")
def load_hours():
    env = os.getenv("BUSINESS_HOURS_JSON")
    if env:
        try: return json.loads(env)
        except Exception: pass
    for p in ("services/ivr/hours.json","hours.json","config/hours.json"):
        if os.path.exists(p):
            with open(p,"r",encoding="utf-8") as f: return json.load(f)
    return {"timezone":"America/New_York","mon":"9:00AM-5:00PM","tue":"9:00AM-5:00PM","wed":"9:00AM-5:00PM","thu":"9:00AM-5:00PM","fri":"9:00AM-5:00PM","sat":"Closed","sun":"Closed"}
def get_forward_number():
    num = (os.getenv("FORWARD_NUMBER") or "").strip()
    if not num: return ""
    if num.startswith("+"): return num
    digits = re.sub(r"\D+","", num)
    if len(digits)==10: return "+1"+digits
    if len(digits)==11 and digits.startswith("1"): return "+"+digits
    return ("+"+digits) if digits else ""
def hours_sentence(_h=None):
    return "Monday through Friday 9 AM to 5 PM, closed Saturday and Sunday"

def route_intent(text):
    t = (text or "").lower().strip()
    if any(k in t for k in ["hour","open","close","closing","time","business hours"]): return "hours"
    if any(k in t for k in ["price","pricing","cost","plan","subscription"]): return "pricing"
    if any(k in t for k in ["location","address","where","directions"]): return "location"
    if any(k in t for k in ["leave a message","voicemail","voice mail","record a message"]): return "voicemail"
    if any(k in t for k in [
        "operator","human","agent","representative","someone","real person","live person",
        "talk to a human","talk to someone","speak to a human","speak to someone",
        "patch me through","transfer me","connect me","customer service","support",
        "talk to a person","put me through","get me a human"
    ]): return "operator"
    if any(k in t for k in ["repeat","again","menu","options"]): return "repeat"
    return "unknown"
@app.route("/", methods=["GET","POST"])
def root(): return "Autonomy IVR up", 200

@app.get("/admin/say-hours")
def say_hours(): return jsonify(load_hours()), 200

@app.route("/twilio/ping", methods=["GET","POST"])
def ping():
    return _xml('<?xml version="1.0" encoding="UTF-8"?><Response><Say>Autonomy IVR is online.</Say><Redirect>/voice</Redirect></Response>')

@app.errorhandler(Exception)
def on_error(e):
    traceback.print_exc(file=sys.stderr)
    return _xml('<?xml version="1.0" encoding="UTF-8"?><Response><Say>Sorry, we hit a snag.</Say><Pause length="1"/><Redirect>/voice</Redirect></Response>')

def menu_twiml():
    prompt = "Welcome to Autonomy Receptionist. You can say things like, what are your hours, pricing, or location."
    hints = "hours, pricing, location, operator, human, speak to a person, address, leave a message, voicemail, connect me"
    return f'<?xml version="1.0" encoding="UTF-8"?><Response><Gather input="speech" action="/voice/route" method="POST" language="en-US" hints="{hints}" timeout="6" speechTimeout="auto"><Say>{prompt}</Say></Gather><Say>No input received.</Say><Redirect>/voice</Redirect></Response>'

@app.route("/voice", methods=["POST","GET"])
def voice(): return _xml(menu_twiml())
def hours_sentence(_h=None):
    return "Monday through Friday 9 AM to 5 PM, closed Saturday and Sunday"

def route_intent(text):
    t = (text or "").lower().strip()
    if any(k in t for k in ["hour","open","close","closing","time","business hours"]): return "hours"
    if any(k in t for k in ["price","pricing","cost","plan","subscription"]): return "pricing"
    if any(k in t for k in ["location","address","where","directions"]): return "location"
    if any(k in t for k in ["leave a message","voicemail","voice mail","record a message"]): return "voicemail"
    if any(k in t for k in [
        "operator","human","agent","representative","someone","real person","live person",
        "talk to a human","talk to someone","speak to a human","speak to someone",
        "patch me through","transfer me","connect me","customer service","support",
        "talk to a person","put me through","get me a human"
    ]): return "operator"
    if any(k in t for k in ["repeat","again","menu","options"]): return "repeat"
    return "unknown"
@app.route("/", methods=["GET","POST"])
def root(): return "Autonomy IVR up", 200

@app.get("/admin/say-hours")
def say_hours(): return jsonify(load_hours()), 200

@app.route("/twilio/ping", methods=["GET","POST"])
def ping():
    return _xml('<?xml version="1.0" encoding="UTF-8"?><Response><Say>Autonomy IVR is online.</Say><Redirect>/voice</Redirect></Response>')

@app.errorhandler(Exception)
def on_error(e):
    traceback.print_exc(file=sys.stderr)
    return _xml('<?xml version="1.0" encoding="UTF-8"?><Response><Say>Sorry, we hit a snag.</Say><Pause length="1"/><Redirect>/voice</Redirect></Response>')

def menu_twiml():
    prompt = "Welcome to Autonomy Receptionist. You can say things like, what are your hours, pricing, or location."
    hints = "hours, pricing, location, operator, human, speak to a person, address, leave a message, voicemail, connect me"
    return f'<?xml version="1.0" encoding="UTF-8"?><Response><Gather input="speech" action="/voice/route" method="POST" language="en-US" hints="{hints}" timeout="6" speechTimeout="auto"><Say>{prompt}</Say></Gather><Say>No input received.</Say><Redirect>/voice</Redirect></Response>'

@app.route("/voice", methods=["POST","GET"])
def voice(): return _xml(menu_twiml())
def menu_twiml():
    prompt = "Welcome to Autonomy Receptionist. You can say things like, what are your hours, pricing, or location."
    hints = "hours, pricing, location, operator, human, speak to a person, address, leave a message, voicemail, connect me"
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather input="speech" action="/voice/route" method="POST"
          language="en-US" hints="{hints}" timeout="6" speechTimeout="auto">
    <Say>{prompt}</Say>
  </Gather>
  <Say>No input received.</Say>
  <Redirect>/voice</Redirect>
</Response>'''

@app.route("/voice", methods=["POST","GET"])
def voice():
    return _xml(menu_twiml())
def menu_twiml():
    prompt = "Welcome to Autonomy Receptionist. You can say things like, what are your hours, pricing, or location."
    hints = "hours, pricing, location, operator, human, speak to a person, address, leave a message, voicemail, connect me"
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather input="speech" action="/voice/route" method="POST"
          language="en-US" hints="{hints}" timeout="6" speechTimeout="auto">
    <Say>{prompt}</Say>
  </Gather>
  <Say>No input received.</Say>
  <Redirect>/voice</Redirect>
</Response>'''

@app.route("/voice", methods=["POST","GET"])
def voice():
    return _xml(menu_twiml())
