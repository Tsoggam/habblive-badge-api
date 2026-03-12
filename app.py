import os
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

API_KEY = os.getenv("API_KEY", "74839432")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

ALL_BADGES = [f"EV26MAR{str(i+1).zfill(2)}" for i in range(100)]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
CORS(app)

def get_user_badges(username):
    res = supabase.table("user_badges") \
        .select("badge") \
        .eq("username", username.lower()) \
        .order("created_at") \
        .execute()
    return [r["badge"] for r in res.data]

def add_user_badge(username, badge):
    supabase.table("user_badges").upsert({
        "username": username.lower(),
        "badge": badge,
        "created_at": int(time.time())
    }, on_conflict="username,badge").execute()

def reset_user_badges(username):
    supabase.table("user_badges") \
        .delete() \
        .eq("username", username.lower()) \
        .execute()

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "online", "version": "5.0"})

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/api/next-badge-cookie", methods=["POST"])
def next_badge_cookie():
    try:
        data = request.json
        if not data:
            return jsonify({"ok": False, "error": "JSON inválido"}), 400

        user = data.get("user")
        key = data.get("key")

        if key != API_KEY:
            return jsonify({"ok": False, "error": "API_KEY inválida"}), 403

        if not user:
            return jsonify({"ok": False, "error": "Usuário não encontrado."}), 400

        badges_entregues = get_user_badges(user)
        badges_faltantes = [b for b in ALL_BADGES if b not in badges_entregues]

        if not badges_faltantes:
            return jsonify({
                "ok": True,
                "badge": None,
                "total_encontrados": len(badges_entregues),
                "faltam": 0,
                "zerou": True
            })

        return jsonify({
            "ok": True,
            "badge": badges_faltantes[0],
            "total_encontrados": len(badges_entregues),
            "faltam": len(badges_faltantes),
            "zerou": False
        })

    except Exception as e:
        return jsonify({"ok": False, "error": f"Erro interno: {str(e)}"}), 500


@app.route("/api/confirm-badge", methods=["POST"])
def confirm_badge():
    try:
        data = request.json
        user = data.get("user")
        key = data.get("key")
        badge = data.get("badge")

        if key != API_KEY:
            return jsonify({"ok": False, "error": "API_KEY inválida"}), 403

        if not user or not badge:
            return jsonify({"ok": False, "error": "user e badge obrigatórios"}), 400

        if badge not in ALL_BADGES:
            return jsonify({"ok": False, "error": "Badge inválido"}), 400

        add_user_badge(user, badge)
        badges = get_user_badges(user)

        return jsonify({
            "ok": True,
            "total_encontrados": len(badges),
            "zerou": len(badges) >= 100
        })

    except Exception as e:
        return jsonify({"ok": False, "error": f"Erro interno: {str(e)}"}), 500


@app.route("/api/user/<username>", methods=["GET"])
def get_user(username):
    key = request.args.get("key")
    if key != API_KEY:
        return jsonify({"ok": False, "error": "API_KEY inválida"}), 403

    badges = get_user_badges(username)
    return jsonify({
        "ok": True,
        "user": username,
        "badges": badges,
        "total": len(badges),
        "zerou": len(badges) >= 100
    })


@app.route("/api/user/<username>", methods=["DELETE"])
def reset_user(username):
    key = request.args.get("key")
    if key != API_KEY:
        return jsonify({"ok": False, "error": "API_KEY inválida"}), 403

    reset_user_badges(username)
    return jsonify({"ok": True, "message": f"{username} resetado"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)