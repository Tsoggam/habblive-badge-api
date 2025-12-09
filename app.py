import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY", "74839432")

ALL_BADGES = [f"EV25DEZ{str(i+1).zfill(2)}" for i in range(100)]

app = Flask(__name__)
CORS(app)

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "online",
        "message": "HabbLive Badge API",
        "version": "3.1",
        "endpoints": {
            "/api/next-badge-cookie": "POST - Recebe lista de badges do Tampermonkey"
        }
    })

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "timestamp": __import__("time").time()})

@app.route("/api/next-badge-cookie", methods=["POST"])
def next_badge_cookie():

    try:
        data = request.json
        
        if not data:
            return jsonify({"ok": False, "error": "JSON inválido"}), 400
        
        user = data.get("user")
        key = data.get("key")
        badges_usuario = data.get("badges", [])
        
        if key != API_KEY:
            return jsonify({"ok": False, "error": "API_KEY inválida"}), 403
        
        if not user:
            return jsonify({"ok": False, "error": "Usuário não informado"}), 400
        
        print(f"\n{'='*60}")
        print(f"🔍 Processando: {user}")
        print(f"📋 Badges recebidos: {len(badges_usuario)}")
        print(f"📋 Badges: {badges_usuario}")
        print(f"{'='*60}\n")
        
        badges_validos = [b for b in badges_usuario if b in ALL_BADGES]
        
        print(f"✅ Badges válidos: {len(badges_validos)}")
        
        badges_faltantes = [b for b in ALL_BADGES if b not in badges_validos]
        
        if len(badges_validos) >= 100:
            print(f"\n🏆 {user} JÁ ZEROU! ({len(badges_validos)}/100)\n")
            return jsonify({
                "ok": True,
                "message": "Usuário já possui todos os badges!",
                "badge": None,
                "found": badges_validos,
                "total_encontrados": len(badges_validos),
                "faltam": 0,
                "zerou": True
            })
        
        next_badge = badges_faltantes[0]
        
        print(f"\n✅ {user} → Próximo: {next_badge} | Total: {len(badges_validos)}/100\n")
        
        return jsonify({
            "ok": True,
            "badge": next_badge,
            "found": badges_validos,
            "total_encontrados": len(badges_validos),
            "faltam": len(badges_faltantes),
            "zerou": False
        })
        
    except Exception as e:
        print(f"❌ Erro crítico: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "ok": False,
            "error": f"Erro interno: {str(e)}"
        }), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 Servidor rodando na porta {port}")
    print(f"🔑 API_KEY configurada: {API_KEY[:4]}...")
    app.run(host="0.0.0.0", port=port, debug=False)