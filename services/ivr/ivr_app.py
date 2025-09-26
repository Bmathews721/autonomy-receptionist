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
@app.errorhandler(Exception)
def on_error(e):
    traceback.print_exc(file=sys.stderr)
    return _xml('<?xml version="1.0" encoding="UTF-8"?><Response><Say>Sorry, we hit a snag.</Say><Pause length="1"/><Redirect>/voice</Redirect></Response>')
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
def _hours_text():
    h = load_hours()
    return "Autonomy Receptionist — Hours: Mon %s; Tue %s; Wed %s; Thu %s; Fri %s; Sat %s; Sun %s" % (
        h.get("mon",""),h.get("tue",""),h.get("wed",""),h.get("thu",""),h.get("fri",""),h.get("sat",""),h.get("sun","")
    )
def _pricing_text(): return "Autonomy Receptionist — Pricing: $200/mo Starter, $300/mo Pro."
def _location_text(): return "Autonomy Receptionist — We operate virtually and support clients anywhere."

@app.route("/voice/sms-offer", methods=["POST","GET"])
def sms_offer():
    include = (request.args.get("include") or "hours").lower()
    body = _hours_text() if include=="hours" else _pricing_text() if include=="pricing" else _location_text()
    enc = quote(body)
    return _xml(f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather input="speech" action="/voice/sms-consent2?include={include}&body={enc}" method="POST"
          language="en-US" timeout="6" speechTimeout="auto">
    <Say>Would you like that sent by text? Say yes to receive a text, or say no to skip.</Say>
  </Gather>
  <Say>No input received.</Say>
  <Redirect>/voice</Redirect>
</Response>''')
@app.route("/voice/sms-consent", methods=["POST","GET"])
def sms_consent():
    speech = (request.values.get("SpeechResult") or "").lower().strip()
    body = unquote(request.args.get("body") or "Autonomy Receptionist")
    said_yes = any(k in speech for k in ["yes","yeah","yep","sure","please","ok","okay","text me","send it"])
    if said_yes and body:
        return _xml(f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Sms>{body}</Sms>
  <Say>Sent. Anything else?</Say>
  <Redirect>/voice</Redirect>
</Response>''')
    return _xml('''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>No problem. Anything else?</Say>
  <Redirect>/voice</Redirect>
</Response>''')
@app.route("/voice/route", methods=["POST","GET"])
def voice_route():
    speech = (request.values.get("SpeechResult") or "").strip()
    intent = route_intent(speech)
    if intent == "hours":
        return _xml('''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Our hours are Monday through Friday, nine A M to five P M. We are closed Saturday and Sunday.</Say>
  <Pause length="1"/>
  <Gather input="speech" action="/voice/sms-consent2?include=hours" method="POST" language="en-US" timeout="6" speechTimeout="auto">
    <Say>Would you like that sent by text? Say yes to receive a text, or say no to skip.</Say>
  </Gather>
  <Say>No input received.</Say>
  <Redirect>/voice</Redirect>
</Response>''')
    if intent == "pricing":
        return _xml('''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Our plans start at two hundred dollars per month, with a three hundred dollar option for added features.</Say>
  <Pause length="1"/>
  <Gather input="speech" action="/voice/sms-consent2?include=pricing" method="POST" language="en-US" timeout="6" speechTimeout="auto">
    <Say>Would you like that sent by text? Say yes to receive a text, or say no to skip.</Say>
  </Gather>
  <Say>No input received.</Say>
  <Redirect>/voice</Redirect>
</Response>''')
    if intent == "location":
        return _xml('''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>We operate virtually, so we can help you from anywhere.</Say>
  <Pause length="1"/>
  <Gather input="speech" action="/voice/sms-consent2?include=location" method="POST" language="en-US" timeout="6" speechTimeout="auto">
    <Say>Would you like that sent by text? Say yes to receive a text, or say no to skip.</Say>
  </Gather>
  <Say>No input received.</Say>
  <Redirect>/voice</Redirect>
</Response>''')
    if intent == "sms_hours":
        return _xml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Sms>{_hours_text()}</Sms>
  <Say>Sent. Anything else?</Say>
  <Redirect>/voice</Redirect>
</Response>""")

    if intent == "sms_pricing":
        return _xml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Sms>{_pricing_text()}</Sms>
  <Say>Sent. Anything else?</Say>
  <Redirect>/voice</Redirect>
</Response>""")

    if intent == "sms_location":
        return _xml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Sms>{_location_text()}</Sms>
  <Say>Sent. Anything else?</Say>
  <Redirect>/voice</Redirect>
</Response>""")

    if intent == "voicemail":
        return _xml('''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Please leave a short message after the tone. When you are done, you can hang up.</Say>
  <Record maxLength="90" playBeep="true" action="/voice/voicemail-done" method="POST"/>
</Response>''')
    if intent == "operator":
        num = get_forward_number()
        if not num:
            return _xml('''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>The operator transfer is not configured yet.</Say>
  <Pause length="1"/><Redirect>/voice</Redirect>
</Response>''')
        return _xml(f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Connecting you now.</Say>
  <Dial timeout="25" answerOnBridge="true" action="/voice/transfer-result" method="POST">
    <Number url="/voice/screen">{num}</Number>
  </Dial>
  <Say>No one could be reached.</Say>
  <Pause length="1"/><Say>Would you like to leave a message?</Say>
  <Record maxLength="90" playBeep="true" action="/voice/voicemail-done" method="POST"/>
</Response>''')
    if intent == "repeat":
        return _xml(menu_twiml())
    return _xml('''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Sorry, I didn’t catch that.</Say>
  <Redirect>/voice</Redirect>
</Response>''')
@app.route("/voice/screen", methods=["GET","POST"])
def screen():
    d = (request.values.get("Digits") or "").strip()
    if d == "1": return _xml('<?xml version="1.0" encoding="UTF-8"?><Response><Say>Connecting.</Say></Response>')
    return _xml('''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather numDigits="1" action="/voice/screen" method="POST" timeout="8">
    <Say>Autonomy demo call. Press 1 to accept.</Say>
  </Gather>
  <Say>No input. Goodbye.</Say>
  <Hangup/>
</Response>''')
@app.route("/voice/transfer-result", methods=["POST","GET"])
def transfer_result():
    status = (request.values.get("DialCallStatus") or "").lower()
    if status in ("completed","answered"):
        return _xml('''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Thanks for speaking with us.</Say>
  <Pause length="1"/><Say>Anything else?</Say>
  <Redirect>/voice</Redirect>
</Response>''')
    return _xml('''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Sorry, we couldn't complete the transfer.</Say>
  <Pause length="1"/><Say>Please leave a short message after the tone.</Say>
  <Record maxLength="90" playBeep="true" action="/voice/voicemail-done" method="POST"/>
</Response>''')

@app.route("/voice/voicemail-done", methods=["POST","GET"])
def voicemail_done():
    return _xml('''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Thanks, we received your message.</Say>
  <Pause length="1"/><Say>Would you like anything else?</Say>
  <Redirect>/voice</Redirect>
</Response>''')

if __name__ == "__main__":
    port = int(os.getenv("PORT","10000"))
    app.run(host="0.0.0.0", port=port)

# --- Override: support "text me …" direct SMS intents ---
def route_intent(text):
    t = (text or "").lower().strip()
    if any(p in t for p in ["text me", "send me a text", "sms", "text", "message me", "send it to me"]):
        if any(k in t for k in ["price","pricing","cost","plan","subscription"]): return "sms_pricing"
        if any(k in t for k in ["location","address","where","directions"]):       return "sms_location"
        return "sms_hours"
    if any(k in t for k in ["hour","open","close","closing","time","business hours"]): return "hours"
    if any(k in t for k in ["price","pricing","cost","plan","subscription"]):          return "pricing"
    if any(k in t for k in ["location","address","where","directions"]):               return "location"
    if any(k in t for k in ["leave a message","voicemail","voice mail","record a message"]): return "voicemail"
    if any(k in t for k in [
        "operator","human","agent","representative","someone","real person","live person",
        "talk to a human","talk to someone","speak to a human","speak to someone",
        "patch me through","transfer me","connect me","customer service","support",
        "talk to a person","put me through","get me a human"
    ]): return "operator"
    if any(k in t for k in ["repeat","again","menu","options"]): return "repeat"
    return "unknown"
@app.route("/debug/intent", methods=["POST","GET"])
def debug_intent():
    speech = (request.values.get("SpeechResult") or request.args.get("q","")).strip()
    return jsonify({"speech": speech, "intent": route_intent(speech)}), 200

# --- SMS feature flags ---
def _sms_allowed():
    return os.getenv("SMS_ENABLED","0").lower() in ("1","true","yes")

def _sms_from_attr():
    svc = (os.getenv("SMS_SERVICE_SID") or "").strip()
    if svc: return f' messagingServiceSid="{svc}"'
    frm = (os.getenv("SMS_FROM") or "").strip()
    if frm: return f' from="{frm}"'
    return ""

@app.route("/voice/sms-consent2", methods=["POST","GET"])
def sms_consent2():
    speech = (request.values.get("SpeechResult") or "").lower().strip()
    body = unquote(request.args.get("body") or "Autonomy Receptionist")
    said_yes = any(k in speech for k in ["yes","yeah","yep","sure","please","ok","okay","text me","send it"])

    if said_yes and _sms_allowed():
        attr = _sms_from_attr()
        return _xml(f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Sms{attr}>{body}</Sms>
  <Say>Sent. Anything else?</Say>
  <Redirect>/voice</Redirect>
</Response>''')

    if said_yes:
        return _xml('''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>We’re voice-only right now, so I’ll skip the text.</Say>
  <Redirect>/voice</Redirect>
</Response>''')

    return _xml('''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>No problem. Anything else?</Say>
  <Redirect>/voice</Redirect>
</Response>''')
