import os
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY", "74839432")

# Lista completa de emblemas (ajuste conforme necessário)
ALL_BADGES = [f"EV25DEZ{str(i+1).zfill(2)}" for i in range(100)]

app = Flask(__name__)
CORS(app)

# Cache simples para evitar requisições repetidas
cache = {}

def extrair_badges_do_perfil(username):
    """
    Extrai os badges diretamente do HTML do perfil
    sem necessidade de Selenium
    """
    try:
        url = f"https://habblive.in/perfil?nome={username}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        badges_encontrados = set()
        
        # Método 1: Busca em divs com id="emblemas"
        emblemas_divs = soup.find_all('div', {'id': 'emblemas'})
        for div in emblemas_divs:
            style = div.get('style', '')
            if 'album1584/' in style:
                match = re.search(r'album1584/([^.]+)\.gif', style)
                if match:
                    badge_name = match.group(1)
                    if badge_name != 'undefined' and badge_name.startswith('EV25DEZ'):
                        badges_encontrados.add(badge_name)
        
        # Método 2: Busca em divs com class="aviso-dentro"
        aviso_divs = soup.find_all('div', {'class': 'aviso-dentro'})
        for div in aviso_divs:
            texto = div.get_text(strip=True)
            if texto.startswith('EV25DEZ'):
                badges_encontrados.add(texto)
        
        return list(badges_encontrados)
        
    except Exception as e:
        print(f"❌ Erro ao processar perfil de {username}: {str(e)}")
        return None

@app.route("/", methods=["GET"])
def home():
    """Rota de teste para verificar se a API está online"""
    return jsonify({
        "status": "online",
        "message": "HabbLive Badge API",
        "version": "1.0"
    })

@app.route("/api/next-badge", methods=["POST"])
def next_badge():
    """
    Endpoint principal: retorna o próximo badge que o usuário NÃO tem
    """
    data = request.json
    user = data.get("user")
    key = data.get("key")
    
    if key != API_KEY:
        return jsonify({"ok": False, "error": "API_KEY inválida"}), 403
    
    if not user:
        return jsonify({"ok": False, "error": "Usuário não informado"}), 400
    
    try:
        # Busca os badges do usuário
        badges_usuario = extrair_badges_do_perfil(user)
        
        if badges_usuario is None:
            return jsonify({
                "ok": False,
                "error": "Não foi possível acessar o perfil do usuário"
            }), 500
        
        # Encontra o próximo badge disponível
        badges_faltantes = [b for b in ALL_BADGES if b not in badges_usuario]
        
        if not badges_faltantes:
            return jsonify({
                "ok": True,
                "message": "Usuário já possui todos os badges!",
                "badge": None,
                "found": badges_usuario,
                "total_encontrados": len(badges_usuario),
                "zerou": True
            })
        
        next_badge = badges_faltantes[0]
        
        print(f"🔍 {user} → Próximo: {next_badge} | Total: {len(badges_usuario)}/100")
        
        return jsonify({
            "ok": True,
            "badge": next_badge,
            "found": badges_usuario,
            "total_encontrados": len(badges_usuario),
            "faltam": len(badges_faltantes),
            "zerou": False
        })
        
    except Exception as e:
        print(f"❌ Erro ao processar {user}: {str(e)}")
        return jsonify({
            "ok": False,
            "error": f"Erro interno: {str(e)}"
        }), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 Servidor rodando na porta {port}")
    app.run(host="0.0.0.0", port=port, debug=False)