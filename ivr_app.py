from services.ivr.ivr_app import app  # re-export the Flask app used by Render
# Optional: quick health route so we can confirm this file is loaded
try:
    from flask import jsonify
    @app.get("/admin/shim-ok")
    def shim_ok():
        return jsonify({"ok": True, "source": "root ivr_app.py shim"})
except Exception:
    pass
