import os
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY", "74839432")
HABBLIVE_USER = os.getenv("HABBLIVE_USER")
HABBLIVE_PASS = os.getenv("HABBLIVE_PASS")

# Lista completa de emblemas
ALL_BADGES = [f"EV25DEZ{str(i+1).zfill(2)}" for i in range(100)]

app = Flask(__name__)
CORS(app)

# Sessão persistente global
session = requests.Session()
session_ativa = False

def fazer_login():
    """
    Faz login no HabbLive e mantém a sessão ativa
    """
    global session_ativa
    
    if not HABBLIVE_USER or not HABBLIVE_PASS:
        print("❌ HABBLIVE_USER ou HABBLIVE_PASS não configurados!")
        return False
    
    try:
        print("🔐 Fazendo login no HabbLive...")
        
        # Acessa a página inicial para pegar cookies
        session.get("https://habblive.in/", timeout=10)
        
        # Faz o login via POST
        login_data = {
            "username": HABBLIVE_USER,
            "password": HABBLIVE_PASS
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': 'https://habblive.in/'
        }
        
        response = session.post(
            "https://habblive.in/login",  # Ajuste se a URL for diferente
            data=login_data,
            headers=headers,
            timeout=10,
            allow_redirects=True
        )
        
        # Verifica se o login foi bem-sucedido
        if response.status_code == 200:
            # Tenta acessar um perfil para confirmar
            test = session.get("https://habblive.in/perfil?nome=MOD_Karl", timeout=10)
            if "emblemas" in test.text.lower():
                session_ativa = True
                print("✅ Login realizado com sucesso!")
                return True
        
        print("❌ Falha no login - verifique as credenciais")
        return False
        
    except Exception as e:
        print(f"❌ Erro ao fazer login: {str(e)}")
        return False

def extrair_badges_do_perfil(username):
    """
    Extrai os badges do perfil usando a sessão autenticada
    """
    global session_ativa
    
    # Se a sessão não está ativa, tenta fazer login
    if not session_ativa:
        if not fazer_login():
            return None
    
    try:
        url = f"https://habblive.in/perfil?nome={username}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://habblive.in/'
        }
        
        response = session.get(url, headers=headers, timeout=10)
        
        # Se receber 401/403, a sessão expirou - refaz login
        if response.status_code in [401, 403]:
            print("⚠️ Sessão expirada, fazendo novo login...")
            session_ativa = False
            if fazer_login():
                response = session.get(url, headers=headers, timeout=10)
            else:
                return None
        
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
        
        # Se não encontrou nada, pode ser que precisa de login novamente
        if not badges_encontrados and "login" in response.text.lower():
            print("⚠️ Página de login detectada, refazendo login...")
            session_ativa = False
            return extrair_badges_do_perfil(username)  # Tenta novamente
        
        return list(badges_encontrados)
        
    except Exception as e:
        print(f"❌ Erro ao processar perfil de {username}: {str(e)}")
        return None

@app.route("/", methods=["GET"])
def home():
    """Rota de teste"""
    return jsonify({
        "status": "online",
        "message": "HabbLive Badge API",
        "version": "2.0",
        "authenticated": session_ativa
    })

@app.route("/api/login", methods=["POST"])
def force_login():
    """Força um novo login (útil para debug)"""
    data = request.json
    key = data.get("key")
    
    if key != API_KEY:
        return jsonify({"ok": False, "error": "API_KEY inválida"}), 403
    
    global session_ativa
    session_ativa = False
    
    if fazer_login():
        return jsonify({"ok": True, "message": "Login realizado com sucesso"})
    else:
        return jsonify({"ok": False, "error": "Falha no login"}), 500

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
                "error": "Não foi possível acessar o perfil. Verifique se as credenciais estão corretas."
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
    # Tenta fazer login ao iniciar
    fazer_login()
    
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 Servidor rodando na porta {port}")
    app.run(host="0.0.0.0", port=port, debug=False)