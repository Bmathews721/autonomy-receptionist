
from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
import os

app = Flask(__name__)

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/voice")
def voice():
    ws = os.getenv("AI_WS_URL", "wss://example.com/stream")
    vr = VoiceResponse()
    with Connect() as c:
        c.stream(url=ws)
    vr.append(c)
    return Response(str(vr), mimetype="text/xml")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT","5000")))
