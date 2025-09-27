from flask import Flask, request, Response, jsonify
import os, json, re, traceback, sys
from urllib.parse import quote, unquote
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

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
    return _xml(smart_menu_twiml())
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
    return _xml(f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>No problem. Anything else?</Say>
  <Redirect>/voice</Redirect>
</Response>''')
@app.route("/voice/screen", methods=["GET","POST"])
def screen():
    d = (request.values.get("Digits") or "").strip()
    if d == "1": return _xml('<?xml version="1.0" encoding="UTF-8"?><Response><Say>Connecting.</Say></Response>')
    return _xml(f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather numDigits="1" action="/voice/screen" method="POST" timeout="8">
    <Say>Autonomy demo call. Press 1 to accept.</Say>
  </Gather>
  <Say>No input. Goodbye.</Say>
  <Hangup/>
</Response>''')
@app.route("/voice/transfer-result", methods=["POST","GET"])
def transfer_result():
    global LAST_TRANSFER
    global LAST_TRANSFER
    global LAST_TRANSFER
    status = (request.values.get("DialCallStatus") or "").lower()
    LAST_TRANSFER = {
        "status": status,
        "dial_sid": (request.values.get("DialCallSid") or ""),
        "to": (request.values.get("To") or ""),
        "from": (request.values.get("From") or "")
    }
    LAST_TRANSFER = {
        "status": status,
        "dial_sid": (request.values.get("DialCallSid") or ""),
        "to": (request.values.get("To") or ""),
        "from": (request.values.get("From") or "")
    }
    LAST_TRANSFER = {
        "status": status,
        "dial_sid": (request.values.get("DialCallSid") or ""),
        "to": (request.values.get("To") or ""),
        "from": (request.values.get("From") or "")
    }
    if status in ("completed","answered"):
        return _xml(f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Thanks for speaking with us.</Say>
  <Pause length="1"/><Say>Anything else?</Say>
  <Redirect>/voice</Redirect>
</Response>''')
    return _xml(f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Sorry, we couldn't complete the transfer.</Say>
  <Pause length="1"/><Say>Please leave a short message after the tone.</Say>
  <Record{_vm_attrs()} maxLength="90" playBeep="true"  action="https://autonomy-ivr.onrender.com/voice/voicemail-done2" method="POST"/>
</Response>''')

@app.route("/voice/voicemail-done", methods=["POST","GET"])
def voicemail_done():
    return _xml(f'''<?xml version="1.0" encoding="UTF-8"?>
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
        return _xml(f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>We’re voice-only right now, so I’ll skip the text.</Say>
  <Redirect>/voice</Redirect>
</Response>''')

    return _xml(f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>No problem. Anything else?</Say>
  <Redirect>/voice</Redirect>
</Response>''')
def _caller_attr():
    cid = (os.getenv("TWILIO_CALLER_ID") or "").strip()
    return f' callerId="{cid}"' if cid else ""
@app.get("/admin/forward")
def admin_forward():
    return jsonify({"forward_number": get_forward_number()}), 200
@app.route("/voice/test-dial", methods=["POST","GET"])
def test_dial():
    num = get_forward_number()
    if not num:
        return _xml('<?xml version="1.0" encoding="UTF-8"?><Response><Say>No forward number is configured.</Say></Response>')
    return _xml(f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Placing a test transfer.</Say>
  <Dial timeout="25" answerOnBridge="true"{_record_attrs()}{_caller_attr()} action="/voice/transfer-result" method="POST">
    <Number>{num}</Number>
  </Dial>
  <Say>We could not complete the test transfer.</Say>
</Response>''')
LAST_TRANSFER = {}
@app.get("/admin/last-transfer")
def admin_last_transfer():
    return jsonify(LAST_TRANSFER or {"info":"none yet"}), 200
from urllib.parse import quote as _q

def _normalize_e164(n):
    import re
    d = re.sub(r'\D+','', n or '')
    if not d: return ''
    if d.startswith('1') and len(d)==11: return '+'+d
    if len(d)==10: return '+1'+d
    return '+'+d

@app.route("/voice/test-call", methods=["GET","POST"])
def test_call():
    num = _normalize_e164(request.args.get("to") or get_forward_number())
    if not num:
        return _xml('<?xml version="1.0" encoding="UTF-8"?><Response><Say>No forward number is configured.</Say></Response>')
    return _xml(f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Placing a test transfer.</Say>
  <Dial timeout="25" answerOnBridge="true"{_record_attrs()}{_caller_attr()} action="/voice/transfer-result" method="POST">
    <Number>{num}</Number>
  </Dial>
  <Say>We could not complete the test transfer.</Say>
</Response>''')

# --- Hours parsing & open/closed check ---
def _parse_range(s):
    s = (s or "").strip().lower()
    if s in ("closed","", "closed.", "close"): return None
    # e.g., "9:00AM-5:00PM"
    import re, datetime as _dt
    m = re.match(r'\s*(\d{1,2}:\d{2}\s*[ap]m)\s*-\s*(\d{1,2}:\d{2}\s*[ap]m)\s*', s, re.I)
    if not m: return None
    def _hm(t):
        t = t.replace(" ", "")
        return _dt.datetime.strptime(t, "%I:%M%p").time()
    return (_hm(m.group(1)), _hm(m.group(2)))

def _is_open_now():
    h = load_hours()
    tz = ZoneInfo(h.get("timezone","America/New_York"))
    now = datetime.now(tz)
    day = ["mon","tue","wed","thu","fri","sat","sun"][now.weekday()]
    rng = _parse_range(h.get(day))
    # Demo override
    if (os.getenv("DEMO_CLOSED","0").lower() in ("1","true","yes")): return False
    if not rng: return False
    start, end = rng
    tnow = now.time()
    return (start <= tnow <= end)

def smart_menu_twiml():
    if _is_open_now():
        return menu_twiml()
    # closed: speak concise hours, offer text, then voicemail
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>We’re currently closed. {hours_sentence(None)}.</Say>
  <Pause length="1"/>
  <Gather input="speech" action="/voice/sms-consent2?include=hours" method="POST"
          language="en-US" timeout="6" speechTimeout="auto">
    <Say>Would you like our hours sent by text? Say yes to receive a text, or say no to skip.</Say>
  </Gather>
  <Say>No input received.</Say>
  <Say>You can also leave a short message after the tone.</Say>
  <Record{_vm_attrs()} maxLength="90" playBeep="true"  action="https://autonomy-ivr.onrender.com/voice/voicemail-done2" method="POST"/>
</Response>'''

# --- Call recording toggle ---
def _record_enabled():
    return os.getenv("CALL_RECORD","0").lower() in ("1","true","yes")

def _record_attrs():
    return ' record="record-from-answer" recordingStatusCallback="/voice/recording-status"' if _record_enabled() else ""

def _record_say():
    return '<Say>For quality and training, this call may be recorded.</Say>' if _record_enabled() else ''

@app.route("/voice/recording-status", methods=["POST","GET"])
def recording_status():
    # minimal ack; you can log request.values if needed
    return ("", 204)

# --- Alert helpers (email first, SMS optional) ---
def _send_email_sg(subject: str, text: str) -> bool:
    api = (os.getenv("SENDGRID_API_KEY") or "").strip()
    to  = (os.getenv("ALERT_EMAIL_TO") or "").strip()
    frm = (os.getenv("ALERT_EMAIL_FROM") or "").strip()
    if not (api and to and frm): return False
    payload = {
        "personalizations":[{"to":[{"email":x.strip()} for x in to.split(",") if x.strip()]}],
        "from":{"email":frm},
        "subject":subject,
        "content":[{"type":"text/plain","value":text}]
    }
    try:
        req = urllib.request.Request(
            "https://api.sendgrid.com/v3/mail/send",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization":f"Bearer {api}","Content-Type":"application/json"}
        )
        urllib.request.urlopen(req, timeout=6).read()
        return True
    except Exception:
        return False

def _send_sms_alert(text: str) -> bool:
    # Only if you want SMS alerts AND your A2P is approved (SMS_ENABLED=1)
    if (os.getenv("SMS_ENABLED","0").lower() not in ("1","true","yes")): return False
    to = (os.getenv("ALERT_SMS_TO") or "").strip()
    if not to: return False
    svc = (os.getenv("SMS_SERVICE_SID") or "").strip()
    frm = (os.getenv("SMS_FROM") or "").strip()
    sid = (os.getenv("ACCOUNT_SID") or os.getenv("TWILIO_ACCOUNT_SID") or "").strip()
    tok = (os.getenv("AUTH_TOKEN") or os.getenv("TWILIO_AUTH_TOKEN") or "").strip()
    if not (sid and tok and (svc or frm)): return False
    data = {"To": to, "Body": text}
    if svc: data["MessagingServiceSid"] = svc
    else:   data["From"] = frm
    try:
        req = urllib.request.Request(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
            data=urllib.parse.urlencode(data).encode("utf-8")
        )
        b64 = base64.b64encode(f"{sid}:{tok}".encode()).decode()
        req.add_header("Authorization", f"Basic {b64}")
        urllib.request.urlopen(req, timeout=6).read()
        return True
    except Exception:
        return False

def _send_alert(subject: str, text: str):
    if _send_email_sg(subject, text): return "email"
    if _send_sms_alert(text):         return "sms"
    return "none"
@app.route("/voice/voicemail-done2", methods=["POST","GET"])
def voicemail_done2():
    rec = (request.values.get("RecordingUrl") or "").strip()
    caller = (request.values.get("From") or "").strip()
    dur = (request.values.get("RecordingDuration") or "").strip()
    if rec:
        try:
            _send_alert("New voicemail",
                f"From: {caller}\nDuration: {dur}s\nRecording: {rec}.mp3")
        except Exception:
            pass
    return _xml(f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Thanks, we received your message.</Say>
  <Pause length="1"/><Say>Would you like anything else?</Say>
  <Redirect>/voice</Redirect>
</Response>''')
@app.route("/voice/transfer-status", methods=["POST","GET"])
def transfer_status():
    global LAST_TRANSFER
    LAST_TRANSFER = {
        "event": (request.values.get("CallStatus") or request.values.get("DialCallStatus") or ""),
        "to": (request.values.get("To") or ""),
        "from": (request.values.get("From") or ""),
        "dial_sid": (request.values.get("DialCallSid") or ""),
        "call_sid": (request.values.get("CallSid") or "")
    }
    return ("", 204)
@app.route("/voice/trigger-operator", methods=["GET","POST"])
def trigger_operator():
    num = get_forward_number()
    if not num:
        return _xml('<?xml version="1.0" encoding="UTF-8"?><Response><Say>The operator transfer is not configured.</Say></Response>')
    return _xml(f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Connecting you now.</Say>
  <Dial timeout="45" answerOnBridge="true"{_caller_attr()} action="https://autonomy-ivr.onrender.com/voice/transfer-result" method="POST"
        statusCallback="https://autonomy-ivr.onrender.com/voice/transfer-status" statusCallbackEvent="initiated ringing answered completed">
    <Number>{num}</Number>
  </Dial>
  <Say>No one could be reached.</Say>
  <Pause length="1"/><Say>Would you like to leave a message?</Say>
  <Record{_vm_attrs()} maxLength="90" playBeep="true"  action="https://autonomy-ivr.onrender.com/voice/voicemail-done2" method="POST"/>
</Response>''')
CAPTURED = {}
def _csid():
    return (request.values.get("CallSid") or request.values.get("ParentCallSid") or "").strip()
@app.route("/voice/capture-start", methods=["POST","GET"])
def capture_start():
    cs = _csid()
    if cs: CAPTURED[cs] = {"name":"", "reason":""}
    return _xml(f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather input="speech" action="https://autonomy-ivr.onrender.com/voice/capture-name" method="POST"
          language="en-US" timeout="6" speechTimeout="auto">
    <Say>Sure. What name should I give our team?</Say>
  </Gather>
  <Say>No input received.</Say>
  <Redirect>/voice</Redirect>
</Response>''')

@app.route("/voice/capture-name", methods=["POST","GET"])
def capture_name():
    cs = _csid()
    speech = (request.values.get("SpeechResult") or "").strip()
    if cs:
        rec = CAPTURED.setdefault(cs, {"name":"", "reason":""})
        if speech: rec["name"] = speech
    return _xml(f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather input="speech" action="https://autonomy-ivr.onrender.com/voice/capture-reason" method="POST"
          language="en-US" timeout="7" speechTimeout="auto">
    <Say>Thanks. Briefly, what is this regarding?</Say>
  </Gather>
  <Say>No input received.</Say>
  <Redirect>/voice</Redirect>
</Response>''')

@app.route("/voice/capture-reason", methods=["POST","GET"])
def capture_reason():
    cs = _csid()
    speech = (request.values.get("SpeechResult") or "").strip()
    name = ""
    if cs:
        rec = CAPTURED.setdefault(cs, {"name":"", "reason":""})
        if speech: rec["reason"] = speech
        name = rec.get("name","")
    safe_name = name or "you"
    reason = CAPTURED.get(cs,{}).get("reason","your request")
    return _xml(f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Thanks, {safe_name}. I\'ll connect you now about {reason}.</Say>
  <Dial timeout="45" answerOnBridge="true"{_caller_attr()} action="https://autonomy-ivr.onrender.com/voice/transfer-result" method="POST"
        statusCallback="https://autonomy-ivr.onrender.com/voice/transfer-status" statusCallbackEvent="initiated ringing answered completed">
    <Number>{get_forward_number()}</Number>
  </Dial>
  <Say>No one could be reached.</Say>
  <Pause length="1"/><Say>Would you like to leave a message?</Say>
  <Record{_vm_attrs()} maxLength="90" playBeep="true"  action="https://autonomy-ivr.onrender.com/voice/voicemail-done2" method="POST"/>
</Response>''')
@app.route("/voice/route", methods=["POST","GET"])
def voice_route():
    speech = (request.values.get("SpeechResult") or "").strip()
    intent = route_intent(speech)

    ans = faq_answer(speech)
    if ans and intent == "unknown":
        enc = quote(ans)
        return _xml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>{ans}</Say>
  <Pause length="1"/>
  <Gather input="speech" action="/voice/sms-consent2?include=faq&body={enc}" method="POST" language="en-US" timeout="6" speechTimeout="auto">
    <Say>Would you like that sent by text? Say yes to receive a text, or say no to skip.</Say>
  </Gather>
  <Say>No input received.</Say>
  <Redirect>/voice</Redirect>
</Response>""")

    if intent == "hours":
        return _xml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Our hours are Monday through Friday, nine A M to five P M. We are closed Saturday and Sunday.</Say>
  <Pause length="1"/>
  <Gather input="speech" action="/voice/sms-consent2?include=hours" method="POST" language="en-US" timeout="6" speechTimeout="auto">
    <Say>Would you like that sent by text? Say yes to receive a text, or say no to skip.</Say>
  </Gather>
  <Say>No input received.</Say>
  <Redirect>/voice</Redirect>
</Response>""")

    if intent == "pricing":
        return _xml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Our plans start at two hundred dollars per month, with a three hundred dollar option for added features.</Say>
  <Pause length="1"/>
  <Gather input="speech" action="/voice/sms-consent2?include=pricing" method="POST" language="en-US" timeout="6" speechTimeout="auto">
    <Say>Would you like that sent by text? Say yes to receive a text, or say no to skip.</Say>
  </Gather>
  <Say>No input received.</Say>
  <Redirect>/voice</Redirect>
</Response>""")

    if intent == "location":
        return _xml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>We operate virtually, so we can help you from anywhere.</Say>
  <Pause length="1"/>
  <Gather input="speech" action="/voice/sms-consent2?include=location" method="POST" language="en-US" timeout="6" speechTimeout="auto">
    <Say>Would you like that sent by text? Say yes to receive a text, or say no to skip.</Say>
  </Gather>
  <Say>No input received.</Say>
  <Redirect>/voice</Redirect>
</Response>""")

    if intent == "voicemail":
        return _xml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Please leave a short message after the tone. When you are done, you can hang up.</Say>
  <Record{_vm_attrs()} maxLength="90" playBeep="true"  action="https://autonomy-ivr.onrender.com/voice/voicemail-done2" method="POST"/>
</Response>""")

    if intent == "operator":
        return _xml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Redirect>https://autonomy-ivr.onrender.com/voice/capture-start</Redirect>
</Response>""")

    if intent == "repeat":
        return _xml(menu_twiml())

    return _xml(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Sorry, I didn’t catch that.</Say>
  <Redirect>/voice</Redirect>
</Response>""")
@app.route("/", methods=["GET"])
def root():
    return "Autonomy IVR up", 200
@app.get("/admin/version")
def version():
    import time
    return jsonify({
        "commit": os.getenv("RENDER_GIT_COMMIT") or os.getenv("COMMIT","local"),
        "ts": time.strftime("%Y-%m-%d %H:%M:%S")
    }), 200

# --- FAQ loader and matcher ---
def load_faq():
    p = "services/ivr/faq.json"
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def faq_answer(text):
    t = (text or "").lower()
    for item in load_faq():
        kws = item.get("keywords", [])
        if any(k in t for k in kws):
            return item.get("answer") or ""
    return ""
@app.get("/admin/faq")
def admin_faq():
    return jsonify(load_faq()), 200

# --- FAQ loader and matcher ---
def load_faq():
    p = "services/ivr/faq.json"
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def faq_answer(text):
    t = (text or "").lower()
    for item in load_faq():
        kws = item.get("keywords", [])
        if any(k in t for k in kws):
            return item.get("answer") or ""
    return ""

# --- Voicemail transcription toggle ---
def _vm_attrs():
    return ' transcribe="true" transcribeCallback="https://autonomy-ivr.onrender.com/voice/vm-transcript"' \
        if os.getenv("VOICEMAIL_TRANSCRIBE","0").lower() in ("1","true","yes") else ""

@app.route("/voice/vm-transcript", methods=["POST","GET"])
def vm_transcript():
    # Twilio sends TranscriptionText, RecordingUrl, From, CallSid, etc.
    txt = (request.values.get("TranscriptionText") or "").strip()
    rec = (request.values.get("RecordingUrl") or "").strip()
    caller = (request.values.get("From") or "").strip()
    sid = (request.values.get("CallSid") or "").strip()
    if txt or rec:
        try:
            body = f"From: {caller}\nCallSid: {sid}\n\nTranscript:\n{txt}\n\nRecording: {rec}.mp3"
            _send_alert("Voicemail transcript", body)
        except Exception:
            pass
    return ("", 204)
