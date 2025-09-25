
import os, requests, datetime, json
from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse
from router import route_intent, intent_prompt
from notifier import send_summary_sms, send_sms_raw
from models import init_db, init_events, insert_call, list_calls, get_call, add_event, metrics_since

USE_OPENAI = os.getenv("USE_OPENAI", "0") == "1"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
BUSINESS_PHONE = os.getenv("BUSINESS_PHONE", "(339) 364-3940")
LOGS_TOKEN = os.getenv("LOGS_TOKEN", "")
DIGEST_TOKEN = os.getenv("DIGEST_TOKEN", "")
DIGEST_SMS_TOKEN = os.getenv("DIGEST_SMS_TOKEN", "")
RELAY_TOKEN = os.getenv("RELAY_TOKEN", "")
INTEGRATION_WEBHOOK_URL = os.getenv("INTEGRATION_WEBHOOK_URL", "")

app = Flask(__name__)
init_db(); init_events()

def load_clients_map():
    try:
        with open(os.path.join(os.path.dirname(__file__), "clients.json"), "r") as f:
            return json.load(f)
    except Exception:
        return {}

def get_client_info(called_number: str):
    clients = load_clients_map()
    return clients.get(called_number) or clients.get(called_number.replace("+1","")) or {}

def speak(vr, text: str, client_info: dict):
    lang = (client_info or {}).get("language")
    voice = (client_info or {}).get("tts_voice")
    kwargs = {}
    if lang: kwargs["language"] = lang
    if voice: kwargs["voice"] = voice
    vr.say(text, **kwargs)

def compute_lead_score(transcript: str, intent: str, client_info: dict):
    cfg = (client_info or {}).get("lead_scoring") or {}
    hot_kw = [w.lower() for w in cfg.get("hot_keywords", [])]
    cold_kw = [w.lower() for w in cfg.get("cold_keywords", [])]
    rules = cfg.get("rules", [])
    t = (transcript or "").lower()
    score = 0; tags = []
    if any(k in t for k in hot_kw): score += 10; tags.append("hot_kw")
    if any(k in t for k in cold_kw): score -= 10; tags.append("cold_kw")
    def contains(x): return x in t
    for r in rules:
        try:
            if eval(r.get("if",""), {"__builtins__": {}}, {"intent": intent, "contains": contains}):
                score += int(r.get("score",0))
        except Exception:
            pass
    return score, tags

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/ivr")
def ivr():
    vr = VoiceResponse()
    called = request.values.get("To", "")
    client_info = get_client_info(called)
    greeting = (client_info or {}).get("preferred_greeting") or "Thanks for calling."
    speak(vr, greeting, client_info)
    speak(vr, "Please tell me how I can help. For example, say, book an appointment, or, what are your hours. Start speaking after the beep.", client_info)
    vr.record(action="/whisper-route", method="POST", max_length=8, play_beep=True, timeout=3)
    speak(vr, "I didn't get that. Let's try again.", client_info)
    vr.redirect("/ivr")
    return Response(str(vr), mimetype="text/xml")

def _transcribe(audio_bytes):
    # Use faster-whisper locally by default (placeholder; real model call omitted)
    # In this rebuild version, we'll skip actual transcription and simulate via Twilio's SpeechResult if present
    return ""

@app.post("/whisper-route")
def whisper_route():
    recording_url = request.form.get("RecordingUrl")
    caller = request.form.get("From", "")
    called = request.form.get("To", "")
    call_sid = request.form.get("CallSid", "")
    vr = VoiceResponse()

    # Try to use Twilio SpeechResult (if using <Gather speech>) as a fallback in this rebuild
    transcript = request.form.get("SpeechResult") or ""
    if (not transcript) and recording_url:
        audio = requests.get(recording_url + ".wav").content
        transcript = _transcribe(audio)

    if not transcript:
        speak(vr, "I didn't catch that. Let's try one more time.", get_client_info(called))
        vr.redirect("/ivr")
        return Response(str(vr), mimetype="text/xml")

    client_info = get_client_info(called)
    intent = route_intent(transcript)

    # Log call
    call_id = insert_call(datetime.datetime.utcnow().isoformat(timespec='seconds'), caller, called, call_sid, intent, transcript, (recording_url + ".wav") if recording_url else "")
    add_event(call_id, "intent_detected", intent)

    # Lead score + hot alert
    score, tags = compute_lead_score(transcript, intent, client_info)
    from models import db
    with db() as conn:
        c = conn.cursor()
        c.execute("UPDATE calls SET lead_score=?, lead_tags=? WHERE id=?", (score, ",".join(tags), call_id))
        conn.commit()

    hot_threshold = ((client_info.get("lead_scoring") or {}).get("hot_threshold") or 9999)
    if score >= hot_threshold:
        owner = client_info.get("sms")
        if owner:
            try:
                send_summary_sms(owner, f"🔥 Hot lead: intent={intent} score={score} from {caller}")
            except Exception: pass

    # Relay payload for CRM/Calendar
    if INTEGRATION_WEBHOOK_URL:
        payload = {
            "client_line": called,
            "timestamp_utc": datetime.datetime.utcnow().isoformat(),
            "caller": caller,
            "intent": intent,
            "lead_score": score,
            "transcript": transcript,
            "recording_url": (recording_url + ".wav") if recording_url else "",
            "tags": tags
        }
        try:
            requests.post(INTEGRATION_WEBHOOK_URL, json=payload, timeout=5)
        except Exception:
            pass

    # Respond path
    speak(vr, intent_prompt(intent, transcript, client_info), client_info)
    if intent in ("hours","location","pricing"):
        with vr.gather(input="speech", action=f"/send-info?intent={intent}", method="POST", timeout=3) as g:
            g.say("Would you like me to text that info to you? Say yes or no after the beep.")
        return Response(str(vr), mimetype="text/xml")

    if intent == "booking":
        schedule_url = (client_info or {}).get("schedule_url", "")
        if schedule_url:
            with vr.gather(input="speech", action="/send-info?intent=booking", method="POST", timeout=3) as g:
                g.say("Would you like me to text you our scheduling link?")
            return Response(str(vr), mimetype="text/xml")

    if intent == "connect_human":
        speak(vr, "Connecting you now.", client_info)
        vr.dial(BUSINESS_PHONE)
    else:
        speak(vr, "Thanks for calling. Goodbye.", client_info)
    return Response(str(vr), mimetype="text/xml")

@app.post("/send-info")
def send_info():
    intent = request.args.get("intent", "")
    speech = (request.form.get("SpeechResult") or "").lower()
    caller = request.form.get("From", "")
    called = request.form.get("To", "")
    client_info = get_client_info(called)
    vr = VoiceResponse()
    if any(w in speech for w in ["yes","yeah","yep","sure","please","ok","okay","send"]):
        body = ""
        if intent == "hours":
            body = f"{client_info.get('name','Our business')} hours: {client_info.get('business_hours','')}"
        elif intent == "location":
            body = f"{client_info.get('name','Our business')} address: {client_info.get('address','')}"
        elif intent == "pricing":
            body = f"{client_info.get('name','Our business')} pricing: {client_info.get('pricing_text','')}"
        elif intent == "booking":
            link = client_info.get("schedule_url","")
            if link: body = f"{client_info.get('name','Our business')} scheduling: {link}"
        if client_info.get("website"):
            if body: body += f" | {client_info['website']}"
        if body:
            try:
                send_sms_raw(caller, body)
                speak(vr, "Okay, I sent you a text with the details.", client_info)
            except Exception:
                speak(vr, "I couldn't send the text just now, but I spoke the details a moment ago.", client_info)
        else:
            speak(vr, "I don't have enough info to text yet.", client_info)
    else:
        speak(vr, "Okay, no problem.", client_info)
    speak(vr, "Thanks for calling. Goodbye.", client_info)
    return Response(str(vr), mimetype="text/xml")

@app.get("/logs.json")
def logs_json():
    provided = request.args.get("token","")
    if LOGS_TOKEN and provided != LOGS_TOKEN:
        return {"error":"unauthorized"}, 401
    rows = list_calls(limit=100)
    data = [{"id": r[0], "created_at": r[1], "caller": r[2], "called": r[3], "call_sid": r[4], "intent": r[5], "recording_url": r[6]} for r in rows]
    return data

@app.get("/logs/<int:call_id>")
def log_detail(call_id: int):
    provided = request.args.get("token","")
    if LOGS_TOKEN and provided != LOGS_TOKEN:
        return {"error":"unauthorized"}, 401
    row = get_call(call_id)
    if not row: return {"error":"not found"}, 404
    return f"""<!doctype html><html><body>
    <h1>Call {row[0]}</h1>
    <p><b>Time:</b> {row[1]}<br><b>Caller:</b> {row[2]}<br><b>Called:</b> {row[3]}<br><b>Intent:</b> {row[5]}</p>
    <p><a href='{row[7]}'>Recording</a></p>
    <h3>Transcript</h3><pre>{row[6]}</pre>
    </body></html>"""

@app.get("/metrics.json")
def metrics():
    provided = request.args.get("token","")
    if LOGS_TOKEN and provided != LOGS_TOKEN:
        return {"error":"unauthorized"}, 401
    return {"last7": metrics_since(7), "last30": metrics_since(30)}

@app.post("/relay/sms")
def relay_sms():
    provided = request.args.get("token","")
    if RELAY_TOKEN and provided != RELAY_TOKEN:
        return {"error":"unauthorized"}, 401
    call_id = int(request.args.get("call_id","0"))
    message = (request.form.get("message") or "").strip()
    if not (call_id and message): return {"error":"missing call_id or message"}, 400
    from models import db
    with db() as conn:
        c = conn.cursor()
        c.execute("SELECT caller FROM calls WHERE id=?", (call_id,))
        row = c.fetchone()
    if not row: return {"error":"call not found"}, 404
    try:
        send_sms_raw(row[0], message)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}, 500

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.getenv("PORT","5001")))

from flask import send_file

@app.route("/admin/fallback-log")
def fallback_log():
    log_path = "logs/fallback.log"
    try:
        return send_file(log_path, mimetype="text/plain", as_attachment=False, download_name="fallback.log")
    except FileNotFoundError:
        return "No fallback log found yet.", 404


from flask import request
from twilio.twiml.voice_response import VoiceResponse

@app.route("/admin/say-hours")
def admin_say_hours():
    # ?called= lets you override which number to look up; defaults to your prod number
    called = request.args.get("called", "+18579579141")
    info = get_client_info(called)
    hours = (info or {}).get("business_hours")
    vr = VoiceResponse()
    if hours:
        speak(vr, f"Our business hours are {hours}.", info)
    else:
        speak(vr, "Sorry, I don’t have our business hours on file.", info)
    return str(vr)

# --- Admin endpoint: force hours TTS ---
from flask import request
from twilio.twiml.voice_response import VoiceResponse

@app.route("/admin/say-hours")
def admin_say_hours():
    called = request.args.get("called", "+18579579141")
    info = get_client_info(called)
    hours = (info or {}).get("business_hours")
    vr = VoiceResponse()
    if hours:
        speak(vr, f"Our business hours are {hours}.", info)
    else:
        speak(vr, "Sorry, I don’t have our business hours on file.", info)
    return str(vr)
