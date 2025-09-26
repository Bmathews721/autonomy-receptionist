from flask import Flask, request, Response, jsonify
import os, json

app = Flask(__name__)

# --- Health / root ---
@app.get("/")
def root():
    return "Autonomy IVR is up", 200

@app.get("/admin/shim-ok")
def shim_ok():
    return "OK", 200

# --- Hours (from env or file) ---
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

@app.get("/admin/say-hours")
def say_hours():
    return jsonify(load_hours()), 200

# --- Twilio Voice webhook (TwiML) ---
@app.post("/voice")
def voice():
    hours = load_hours()
    say_hours_brief = f"Mon {hours['mon']}, Tue {hours['tue']}, Wed {hours['wed']}, Thu {hours['thu']}, Fri {hours['fri']}, Sat {hours['sat']}, Sun {hours['sun']}."
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather input="dtmf" numDigits="1" action="/voice/menu">
    <Say>Welcome to Autonomy Receptionist. Press 1 to hear our business hours.</Say>
  </Gather>
  <Say>No input received. {say_hours_brief}</Say>
  <Hangup/>
</Response>"""
    return Response(twiml, mimetype="text/xml")

@app.post("/voice/menu")
def voice_menu():
    digit = (request.form.get("Digits") or "").strip()
    if digit == "1":
        hours = load_hours()
        say_hours_brief = f"Our hours are: Mon {hours['mon']}, Tue {hours['tue']}, Wed {hours['wed']}, Thu {hours['thu']}, Fri {hours['fri']}, Sat {hours['sat']}, Sun {hours['sun']}."
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>{say_hours_brief}</Say>
  <Hangup/>
</Response>"""
    else:
        twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Invalid selection. Goodbye.</Say>
  <Hangup/>
</Response>"""
    return Response(twiml, mimetype="text/xml")

if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
