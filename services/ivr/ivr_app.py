from flask import Flask, request, Response, jsonify
import os, json, re, traceback, sys

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

def route_intent(text):
    t = (text or "").lower().strip()
    # Basic keyword intents
    if any(k in t for k in ["hour", "open", "close", "closing", "time"]): return "hours"
    if any(k in t for k in ["location", "address", "where", "directions"]): return "location"
    if any(k in t for k in ["price", "pricing", "cost", "plan", "subscription"]): return "pricing"
    if any(k in t for k in ["operator", "person", "human", "agent", "representative", "someone"]): return "operator"
    if any(k in t for k in ["repeat", "again", "what did you say"]): return "repeat"
    return "unknown"

@app.route("/", methods=["GET","POST"])
def root(): return "Autonomy IVR up", 200

@app.get("/admin/say-hours")
def say_hours(): return jsonify(load_hours()), 200

@app.route("/twilio/ping", methods=["GET","POST"])
def ping(): return _xml(_say("Autonomy IVR is online."))
# Global error handler: always return valid TwiML
@app.errorhandler(Exception)
def on_error(e):
    traceback.print_exc(file=sys.stderr)
    return _xml(_say("Sorry, we hit a snag. Please call back shortly."))

# ENTRY: speech + dtmf
@app.route("/voice", methods=["POST","GET"])
def voice():
    prompt = ("Welcome to Autonomy Receptionist. "
              "You can say things like, what are your hours, pricing, or location. "
              "Or press 1 for hours, 2 for pricing, 3 for location, or 0 for an operator.")
    # Hints help Twilio ASR
    hints = "hours, pricing, location, operator, human, speak to a person, address"
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather input="speech dtmf" numDigits="1" action="/voice/route" method="POST"
          language="en-US" hints="{hints}" timeout="6" speechTimeout="auto">
    <Say>{prompt}</Say>
  </Gather>
  <Say>No input received. Please call again later.</Say>
  <Hangup/>
</Response>"""
    return _xml(twiml)

# ROUTER: handle speech or digit
@app.route("/voice/route", methods=["POST","GET"])
def voice_route():
    digit = (request.values.get("Digits") or "").strip()
    speech = (request.values.get("SpeechResult") or "").strip()
    intent = None

    if digit:
        intent = {"1":"hours","2":"pricing","3":"location","0":"operator"}.get(digit, "unknown")
    else:
        intent = route_intent(speech)

    if intent == "hours":
        brief = hours_sentence(load_hours())
        return _xml(_say(f"Our hours are: {brief}"))
    if intent == "pricing":
        return _xml(_say("Our plans start at two hundred dollars per month, with options at three hundred dollars as well."))
    if intent == "location":
        # Customize if you want a real address; placeholder for now
        return _xml(_say("We are a virtual service. You can reach us online any time."))
    if intent == "operator":
        # Simple voicemail-style fallback (hangs up after message). Replace with <Dial> if you have a live target.
        return _xml(_say("Please leave a message after the tone. Goodbye."))
    if intent == "repeat":
        return voice()

    # Unknown → reprompt once
    reprompt = ("Sorry, I didn't catch that. "
                "You can say hours, pricing, or location. "
                "Or press 1 for hours, 2 for pricing, 3 for location, 0 for an operator.")
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather input="speech dtmf" numDigits="1" action="/voice/route" method="POST"
          language="en-US" hints="hours, pricing, location, operator" timeout="6" speechTimeout="auto">
    <Say>{reprompt}</Say>
  </Gather>
  <Say>No input received. Goodbye.</Say>
  <Hangup/>
</Response>"""
    return _xml(twiml)
if __name__ == "__main__":
    port = int(os.getenv("PORT","10000"))
    app.run(host="0.0.0.0", port=port)
