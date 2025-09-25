
# Autonomy Receptionist – Pro Plus Demo (Rebuild)

This repo contains a deployable AI receptionist stack:
- Twilio **/ivr** with transcription placeholder, intent routing, **client-specific info** from `clients.json`
- Post-call summaries, **daily digests**, **logs + metrics**, **lead scoring + hot alerts**
- Caller SMS follow-ups ("text me the info"), **booking link SMS**, **custom greetings**, **special requests**
- **CRM relay**, **SMS relay**, **multi-language Say()**

## Quick start
```bash
docker compose up --build -d
# webhook: http://localhost:5000/voice
# ivr:     http://localhost:5001/ivr
```

## Env (IVR)
- TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_FROM
- LOGS_TOKEN, RELAY_TOKEN, DIGEST_TOKEN, DIGEST_SMS_TOKEN
- INTEGRATION_WEBHOOK_URL (optional)

## Client config
Edit `services/ivr/clients.json` (keyed by called number). Includes:
- business_hours, address, pricing_text, website
- preferred_greeting, special_requests, schedule_url
- language, tts_voice
- lead_scoring rules

## Deploy
Use Docker anywhere or the Render blueprint in `cloud_deploy_configs/render/render.yaml`.
