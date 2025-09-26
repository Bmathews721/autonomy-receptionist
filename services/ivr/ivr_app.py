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
  <Gather input="speech dtmf" numDigits="1" action="/voice/route" method="POST"
          language="en-US" hints="{hints}" timeout="6" speechTimeout="auto">
    <Say>{prompt}</Say>
  </Gather>
  <Say>No input received.</Say>
  <Redirect>/voice</Redirect>
</Response>"""

@app.route("/voice", methods=["POST","GET"])
def voice():
    return _xml(menu_twiml())
@app.route("/voice/route", methods=["POST","GET"])
def voice_route():
    digit = (request.values.get("Digits") or "").strip()
    speech = (request.values.get("SpeechResult") or "").strip()
    intent = {"1":"hours","2":"pricing","3":"location","0":"operator"}.get(digit) if digit else route_intent(speech)

    if intent == "hours":
        brief = hours_sentence(load_hours())
        return _xml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Our hours are: {brief}.</Say>
  <Pause length="1"/>
  <Say>Would you like anything else?</Say>
  <Redirect>/voice</Redirect>
</Response>""")

    if intent == "pricing":
        return _xml("""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Our plans start at two hundred dollars per month, with a three hundred dollar option for added features.</Say>
  <Pause length="1"/>
  <Say>Would you like anything else?</Say>
  <Redirect>/voice</Redirect>
</Response>""")

    if intent == "location":
        return _xml("""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>We operate virtually, so we can help you from anywhere.</Say>
  <Pause length="1"/>
  <Say>Would you like anything else?</Say>
  <Redirect>/voice</Redirect>
</Response>""")

    if intent == "operator":
        # Demo voicemail flow (replace with <Dial>+15551234567</Dial> for live forward)
        return _xml("""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Okay, please leave a short message after the tone. When you're done, you can simply hang up.</Say>
  <Record maxLength="60" playBeep="true" action="/voice/voicemail-done" method="POST"/>
</Response>""")

    if intent == "repeat":
        return _xml(menu_twiml())

    # Unknown → reprompt then back to menu
    return _xml("""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Sorry, I didn't catch that.</Say>
  <Redirect>/voice</Redirect>
</Response>""")

@app.route("/voice/voicemail-done", methods=["POST","GET"])
def voicemail_done():
    return _xml("""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Thanks, we received your message.</Say>
  <Pause length="1"/>
  <Say>Anything else?</Say>
  <Redirect>/voice</Redirect>
</Response>""")

if __name__ == "__main__":
    port = int(os.getenv("PORT","10000"))
    app.run(host="0.0.0.0", port=port)
