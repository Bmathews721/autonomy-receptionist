from flask import Flask, request, Response
import os

app = Flask(__name__)

def twiml(msg):
    return f'<?xml version="1.0" encoding="UTF-8"?><Response><Say>{msg}</Say><Hangup/></Response>'

@app.route("/", methods=["GET","POST"])
def root():
    return "Autonomy IVR up", 200

@app.route("/voice", methods=["POST","GET"])
def voice():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather input="dtmf" numDigits="1" action="/voice/menu" method="POST">
    <Say>Welcome to Autonomy Receptionist. Press 1 to hear our hours.</Say>
  </Gather>
  <Say>No input received. Goodbye.</Say>
  <Hangup/>
</Response>"""
    return Response(xml, mimetype="text/xml")

@app.route("/voice/menu", methods=["POST","GET"])
def voice_menu():
    digit = (request.values.get("Digits") or "").strip()
    if digit == "1":
        return Response(twiml("Our hours are 9 AM to 5 PM Monday through Friday."), mimetype="text/xml")
    return Response(twiml("Invalid choice. Goodbye."), mimetype="text/xml")

if __name__ == "__main__":
    port = int(os.getenv("PORT","10000"))
    app.run(host="0.0.0.0", port=port)
