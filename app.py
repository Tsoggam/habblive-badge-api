import os, time
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

API_KEY     = os.getenv("API_KEY", "74839432")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
app = Flask(__name__)
CORS(app)

def badge(n): return f"EV26MAR{str(n).zfill(2)}"

def get_level(username):
    res = supabase.table("user_progress") \
        .select("level") \
        .eq("username", username.lower()) \
        .maybe_single() \
        .execute()
    return res.data["level"] if res.data else None

def set_level(username, level):
    supabase.table("user_progress").upsert({
        "username": username.lower(),
        "level": level,
        "updated_at": int(time.time())
    }, on_conflict="username").execute()


@app.route("/api/next-badge", methods=["POST"])
def next_badge():
    data = request.json or {}
    user     = data.get("user", "").strip()
    key      = data.get("key")
    ws_level = data.get("ws_level")  # int ou None, capturado pelo frontend

    if key != API_KEY:
        return jsonify({"ok": False, "error": "API_KEY inválida"}), 403
    if not user:
        return jsonify({"ok": False, "error": "user obrigatório"}), 400

    db_level = get_level(user)

    # Prioridade: supabase > ws_packet > zero
    if db_level is not None:
        current = db_level
        source  = "supabase"
    elif ws_level is not None:
        current = int(ws_level)
        set_level(user, current)  # seed inicial
        source  = "ws_packet"
    else:
        current = 0
        source  = "none"

    if current >= 100:
        return jsonify({"ok": True, "zerou": True, "total": 100})

    next_level = current + 1
    return jsonify({
        "ok":         True,
        "zerou":      False,
        "badge":      badge(next_level),
        "next_level": next_level,
        "current":    current,
        "source":     source
    })


@app.route("/api/confirm-badge", methods=["POST"])
def confirm_badge():
    data = request.json or {}
    user  = data.get("user", "").strip()
    key   = data.get("key")
    level = data.get("level")

    if key != API_KEY:
        return jsonify({"ok": False, "error": "API_KEY inválida"}), 403
    if not user or level is None:
        return jsonify({"ok": False, "error": "user e level obrigatórios"}), 400

    set_level(user, int(level))
    return jsonify({"ok": True, "level": int(level), "zerou": int(level) >= 100})


@app.route("/api/user/<username>", methods=["GET"])
def get_user(username):
    if request.args.get("key") != API_KEY:
        return jsonify({"ok": False, "error": "API_KEY inválida"}), 403
    level = get_level(username)
    return jsonify({"ok": True, "user": username, "level": level, "zerou": level >= 100 if level else False})


@app.route("/api/user/<username>", methods=["DELETE"])
def reset_user(username):
    if request.args.get("key") != API_KEY:
        return jsonify({"ok": False, "error": "API_KEY inválida"}), 403
    supabase.table("user_progress").delete().eq("username", username.lower()).execute()
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), debug=False)