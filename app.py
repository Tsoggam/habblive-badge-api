import os
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY", "74839432")

# Lista completa de emblemas
ALL_BADGES = [f"EV25DEZ{str(i+1).zfill(2)}" for i in range(100)]

app = Flask(__name__)
CORS(app)

def extrair_badges_com_cookies(username, cookies_str):
    """
    Extrai badges usando cookies fornecidos
    """
    try:
        url = f"https://habblive.in/perfil?nome={username}"
        
        # Converte string de cookies em dicionário
        cookies_dict = {}
        for cookie in cookies_str.split('; '):
            if '=' in cookie:
                key, value = cookie.split('=', 1)
                cookies_dict[key] = value
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://habblive.in/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        response = requests.get(url, headers=headers, cookies=cookies_dict, timeout=15, allow_redirects=True)
        
        # Debug: mostra status
        print(f"📡 Status: {response.status_code} | URL: {response.url}")
        print(f"🍪 Cookies enviados: {len(cookies_dict)} cookies")
        
        if response.status_code != 200:
            print(f"❌ Status code: {response.status_code}")
            return None, f"HTTP {response.status_code}"
        
        # Verifica se foi redirecionado para login
        if "login" in response.url.lower() or "/entrar" in response.url.lower():
            print("❌ Redirecionado para página de login")
            return None, "Sessão expirou - faça login novamente no navegador"
        
        soup = BeautifulSoup(response.text, 'html.parser')
        badges_encontrados = set()
        
        # Método 1: Busca em divs com id="emblemas"
        emblemas_divs = soup.find_all('div', {'id': 'emblemas'})
        print(f"🔍 Encontrou {len(emblemas_divs)} divs com id='emblemas'")
        
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
        print(f"🔍 Encontrou {len(aviso_divs)} divs com class='aviso-dentro'")
        
        for div in aviso_divs:
            texto = div.get_text(strip=True)
            if texto.startswith('EV25DEZ'):
                badges_encontrados.add(texto)
        
        # Método 3: Busca no HTML bruto
        html_text = response.text
        matches = re.findall(r'EV25DEZ\d{2}', html_text)
        for match in matches:
            badges_encontrados.add(match)
        
        print(f"✅ Total de badges encontrados: {len(badges_encontrados)}")
        
        # REMOVIDA a verificação de "login" ou "entrar" no HTML
        # pois pode causar falsos positivos
        
        # Se não encontrou nenhum badge, verifica se o perfil existe
        if len(badges_encontrados) == 0:
            # Verifica se há indicação de que é uma página de perfil válida
            if soup.find('div', {'class': 'profile'}) or soup.find('div', {'id': 'profile'}):
                print("⚠️ Perfil válido, mas sem badges EV25DEZ")
                return [], None  # Retorna lista vazia, não erro
            else:
                print("❌ Página de perfil não reconhecida")
                # Salva HTML para debug (opcional)
                with open('debug_page.html', 'w', encoding='utf-8') as f:
                    f.write(html_text)
                return None, "Não foi possível acessar o perfil - verifique se está logado"
        
        return list(badges_encontrados), None
        
    except requests.exceptions.Timeout:
        return None, "Timeout ao acessar HabbLive"
    except requests.exceptions.RequestException as e:
        return None, f"Erro de requisição: {str(e)}"
    except Exception as e:
        return None, f"Erro ao processar: {str(e)}"

@app.route("/", methods=["GET"])
def home():
    """Rota de teste"""
    return jsonify({
        "status": "online",
        "message": "HabbLive Badge API",
        "version": "2.1",
        "endpoints": {
            "/api/next-badge-cookie": "POST - Usa cookies do browser"
        }
    })

@app.route("/api/health", methods=["GET"])
def health():
    """Health check"""
    return jsonify({"status": "ok", "timestamp": __import__("time").time()})

@app.route("/api/next-badge-cookie", methods=["POST"])
def next_badge_cookie():
    """
    Endpoint que usa cookies enviados pelo Tampermonkey
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({"ok": False, "error": "JSON inválido"}), 400
        
        user = data.get("user")
        key = data.get("key")
        cookies_str = data.get("cookies") or request.headers.get("Cookie", "")
        
        # Validações
        if key != API_KEY:
            return jsonify({"ok": False, "error": "API_KEY inválida"}), 403
        
        if not user:
            return jsonify({"ok": False, "error": "Usuário não informado"}), 400
        
        if not cookies_str:
            return jsonify({"ok": False, "error": "Cookies não fornecidos"}), 400
        
        print(f"🔍 Buscando badges de: {user}")
        print(f"🍪 Cookies recebidos: {cookies_str[:100]}...")
        
        # Extrai badges
        badges_usuario, error = extrair_badges_com_cookies(user, cookies_str)
        
        if error:
            return jsonify({
                "ok": False,
                "error": error
            }), 500
        
        if badges_usuario is None:
            return jsonify({
                "ok": False,
                "error": "Não foi possível extrair badges - verifique se está logado"
            }), 500
        
        # Calcula badges faltantes
        badges_faltantes = [b for b in ALL_BADGES if b not in badges_usuario]
        
        # Verifica se zerou
        if not badges_faltantes:
            return jsonify({
                "ok": True,
                "message": "Usuário já possui todos os badges!",
                "badge": None,
                "found": badges_usuario,
                "total_encontrados": len(badges_usuario),
                "faltam": 0,
                "zerou": True
            })
        
        next_badge = badges_faltantes[0]
        
        print(f"✅ {user} → Próximo: {next_badge} | Total: {len(badges_usuario)}/100")
        
        return jsonify({
            "ok": True,
            "badge": next_badge,
            "found": badges_usuario,
            "total_encontrados": len(badges_usuario),
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