

def _rotate_fallback_log(path="logs/fallback.log", max_bytes=1_000_000, backups=5):
    import os, shutil
    try:
        if not os.path.exists(path):
            return
        if os.path.getsize(path) < max_bytes:
            return
        # Rotate: fallback.log -> fallback.log.1 -> ...
        for i in range(backups, 0, -1):
            src = f"{path}.{i-1}" if i>1 else path
            dst = f"{path}.{i}"
            if os.path.exists(src):
                try: os.replace(src, dst)
                except Exception: pass
    except Exception:
        pass

def route_intent(text: str) -> str:
    t = (text or "").lower()
    if any(k in t for k in ["book", "appointment", "schedule", "reserve"]):
        return "booking"
    if any(k in t for k in ["hour", "open", "close", "opening", "closing"]):
        return "hours"
    if any(k in t for k in ["price", "cost", "how much", "rate", "pricing"]):
        return "pricing"
    if any(k in t for k in ["address", "where are you", "location", "directions"]):
        return "location"
    if any(k in t for k in ["human", "representative", "agent", "talk to someone", "operator"]):
        return "connect_human"
    if any(k in t for k in ["sales", "solicitation", "offer", "pitch"]):
        return "decline_solicitation"
    return "fallback"

def intent_prompt(intent: str, text: str, client_info: dict | None = None) -> str:
    # 🔒 Global fallback: always answer if caller mentions hours/open/close
    text_l = text.lower()
    hours = (client_info or {}).get("business_hours")
    if any(word in text_l for word in ("hours", "open", "close")):
        if hours:
            return f"Our business hours are {hours}."
        else:
            return "Sorry, I don’t have our business hours on file."
    if intent == "booking":
        return "I can help with booking. What date and time works best for you? You can also leave your name and number."
    if intent == "hours":
        hours = (client_info or {}).get("business_hours")
    # Fallback: respond if user mentions hours, open, or close
    text_l = text.lower()
    if any(word in text_l for word in ("hours", "open", "close")):
        if hours:
            return f"Our business hours are {hours}."
        else:
            return "Sorry, I don’t have our business hours on file."
    if "hours" in text.lower():
        if hours:
            return f"Our business hours are {hours}."
        else:
            return "Sorry, I don’t have our business hours on file."
    if intent.lower() in ("hours", "business hours", "when are you open", "open hours"):
        if hours:
            return f"Our business hours are {hours}."
        else:
            return "Sorry, I don’t have our business hours on file."
        return hours or "Our typical hours are nine a m to five p m, Monday through Friday. Holiday hours may vary."
    if intent == "pricing":
        pricing = (client_info or {}).get("pricing_text")
        return pricing or "Our pricing is simple and affordable. I can text you the current plan details or connect you to a representative."
    if intent == "location":
        addr = (client_info or {}).get("address")
        return f"Our address is {addr}." if addr else "We are local and serve your area. I can text you our address and directions."
    if intent == "connect_human":
        return "Sure, I'll connect you to a representative now."
    if intent == "decline_solicitation":
        return "Thanks for reaching out. We aren't accepting sales or solicitation calls. Have a great day."
    # 🛡️ Final fallback: never go silent
    return ("I can help with our business hours, address, or pricing. Please ask about one of those.")
    # 🛡️ Final fallback: never go silent
    return ("I can help with our business hours, address, or pricing. Please ask about one of those.")
    # 🛡️ Final fallback: never go silent + log unknown requests
    try:
        print("=== FALLBACK TRIGGERED ===")
        print("Unmatched text:", repr(text))
        print("Known client:", client_info.get('name') if client_info else None)
    except Exception as e:
        print("Fallback logging error:", e)

    return ("I can help with our business hours, address, or pricing. Please ask about one of those.")
    # 🛡️ Final fallback: never go silent + log unknown requests
    import os
    from datetime import datetime

    try:
        os.makedirs("logs", exist_ok=True)
                log_fallback_event(text, client_info)
        print("=== FALLBACK TRIGGERED ===", repr(text))
    except Exception as e:
        print("Fallback logging error:", e)

    return ("I can help with our business hours, address, or pricing. Please ask about one of those.")
    return "I can help with booking, hours, pricing, or connecting you to a representative. What would you like to do?"

# --- helper: fallback logging (unit-testable) ---
from datetime import datetime
import os

def log_fallback_event(text, client_info):
    """
    Append a single structured line to logs/fallback.log and print a debug line.
    Safe to call even if logs dir/file doesn't exist.
    """
    try:
        os.makedirs("logs", exist_ok=True)
        name = client_info.get('name') if client_info else None
        line = f"[{datetime.utcnow().isoformat()}] text={repr(text)} client={repr(name)}\n"
        with open("logs/fallback.log", "a", encoding="utf-8") as f:
            f.write(line)
        print("=== FALLBACK TRIGGERED ===", repr(text))
    except Exception as e:
        print("Fallback logging error:", e)
