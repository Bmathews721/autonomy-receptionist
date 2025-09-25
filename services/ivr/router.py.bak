
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
    if intent == "booking":
        return "I can help with booking. What date and time works best for you? You can also leave your name and number."
    if intent == "hours":
        hours = (client_info or {}).get("business_hours")
    # Fallback: if user text mentions "hours", always reply with business_hours
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
    return "I can help with booking, hours, pricing, or connecting you to a representative. What would you like to do?"
