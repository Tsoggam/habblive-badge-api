import os
import time
import traceback
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

API_KEY      = os.getenv("API_KEY", "74839432")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL e SUPABASE_KEY são obrigatórios")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
CORS(app)

# ─── Helpers ─────────────────────────────────────────────────────────────────

def badge_code(n: int) -> str:
    return f"EV26ABR{str(n).zfill(2)}"

def get_level(username: str):
    """Retorna o level atual do usuário ou None se não existir."""
    try:
        res = supabase.table("user_progress") \
            .select("level") \
            .eq("username", username.lower()) \
            .limit(1) \
            .execute()
        return res.data[0]["level"] if res.data else None
    except Exception as e:
        print(f"[get_level] ERRO para '{username}': {e}")
        traceback.print_exc()
        raise

def set_level(username: str, level: int):
    """Cria ou atualiza o level do usuário."""
    try:
        supabase.table("user_progress").upsert({
            "username":   username.lower(),
            "level":      int(level),
            "updated_at": int(time.time())
        }, on_conflict="username").execute()
    except Exception as e:
        print(f"[set_level] ERRO para '{username}' level={level}: {e}")
        traceback.print_exc()
        raise

# ─── Rotas ───────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "online", "version": "6.0"})

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/next-badge", methods=["POST"])
def next_badge():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"ok": False, "error": "JSON inválido"}), 400

        user     = (data.get("user") or "").strip()
        key      = data.get("key")
        ws_level = data.get("ws_level")  # int capturado pelo pacote WS, pode ser None

        if key != API_KEY:
            return jsonify({"ok": False, "error": "API_KEY inválida"}), 403

        if not user:
            return jsonify({"ok": False, "error": "Campo 'user' obrigatório"}), 400

        db_level = get_level(user)

        # Prioridade: supabase > pacote WS > zero
        if db_level is not None:
            current = db_level
            source  = "supabase"
        elif ws_level is not None:
            current = int(ws_level)
            set_level(user, current)   # seed inicial pelo pacote WS
            source  = "ws_packet"
        else:
            current = 0
            source  = "none"

        if current >= 100:
            return jsonify({
                "ok":    True,
                "zerou": True,
                "total": 100,
                "source": source
            })

        next_level = current + 1
        return jsonify({
            "ok":         True,
            "zerou":      False,
            "badge":      badge_code(next_level),
            "next_level": next_level,
            "current":    current,
            "source":     source
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": f"Erro interno: {str(e)}"}), 500


@app.route("/api/confirm-badge", methods=["POST"])
def confirm_badge():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"ok": False, "error": "JSON inválido"}), 400

        user  = (data.get("user") or "").strip()
        key   = data.get("key")
        level = data.get("level")

        if key != API_KEY:
            return jsonify({"ok": False, "error": "API_KEY inválida"}), 403

        if not user or level is None:
            return jsonify({"ok": False, "error": "Campos 'user' e 'level' obrigatórios"}), 400

        level = int(level)
        if level < 1 or level > 100:
            return jsonify({"ok": False, "error": "Level deve ser entre 1 e 100"}), 400

        set_level(user, level)

        return jsonify({
            "ok":    True,
            "level": level,
            "zerou": level >= 100
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": f"Erro interno: {str(e)}"}), 500


@app.route("/api/user/<username>", methods=["GET"])
def get_user(username):
    try:
        if request.args.get("key") != API_KEY:
            return jsonify({"ok": False, "error": "API_KEY inválida"}), 403

        level = get_level(username)
        return jsonify({
            "ok":    True,
            "user":  username,
            "level": level,
            "zerou": (level or 0) >= 100
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": f"Erro interno: {str(e)}"}), 500


@app.route("/api/user/<username>", methods=["DELETE"])
def reset_user(username):
    try:
        if request.args.get("key") != API_KEY:
            return jsonify({"ok": False, "error": "API_KEY inválida"}), 403

        supabase.table("user_progress") \
            .delete() \
            .eq("username", username.lower()) \
            .execute()

        return jsonify({"ok": True, "message": f"{username} resetado"})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": f"Erro interno: {str(e)}"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)