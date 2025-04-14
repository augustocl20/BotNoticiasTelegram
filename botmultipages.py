import requests
from bs4 import BeautifulSoup
import asyncio
from telegram import Bot
from telegram.error import TelegramError
import threading
from flask import Flask
import os
from urllib.parse import urlsplit, urlunsplit, urljoin
from datetime import datetime

# Configuración
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("❌ Faltan variables de entorno BOT_TOKEN o CHAT_ID")

bot = Bot(token=BOT_TOKEN)
enviados = set()

# Configuración de sitios a scrapear (¡Añade más aquí!)
SITIOS = {
    "La República - Espectáculos": {
        "url": "https://larepublica.pe/espectaculos",
        "contenedor": "div.ListSection_list__Ew_UF",
        "items": "div.ListSection_list__section--item__zeP_z",
        "titulo": "h2 a",
        "enlace": lambda x: urljoin("https://larepublica.pe", x.find('h2').find('a')['href']),
        "imagen": lambda x: x.find('img')['src'] if x.find('img') else None,
        "detalle": {
            "texto": "div.html-content p",
            "imagen": "div.image-container img"
        }
    },
    "Ejemplo Otro Sitio": {  # Plantilla para agregar más
        "url": "https://www.otrasitio.com/entretenimiento",
        "contenedor": "div.article-list",
        "items": "div.article",
        "titulo": "h3 a",
        "enlace": lambda x: x.find('h3').find('a')['href'],
        "imagen": lambda x: x.find('img')['data-src'] if x.find('img') else None,
        "detalle": {
            "texto": "div.article-body p",
            "imagen": "figure.lead-image img"
        }
    }
}

# Helper para URLs canónicas
def canon(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))

# Obtener noticias de un sitio específico
def obtener_noticias(sitio: str):
    config = SITIOS[sitio]
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
        response = requests.get(config["url"], headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        noticias = []
        contenedor = soup.select_one(config["contenedor"])

        if not contenedor:
            print(f"❌ No se encontró el contenedor en {sitio}")
            return noticias

        items = contenedor.select(config["items"])

        for item in items:
            try:
                titulo = item.select_one(config["titulo"]).get_text(strip=True)
                enlace = config["enlace"](item) if callable(config["enlace"]) else item.select_one(config["enlace"])['href']
                imagen = config["imagen"](item) if callable(config["imagen"]) else (item.select_one(config["imagen"])['src'] if item.select_one(config["imagen"]) else None)
                
                if titulo and enlace:
                    noticias.append({
                        "sitio": sitio,
                        "titulo": titulo,
                        "enlace": enlace,
                        "imagen": imagen
                    })
            except Exception as e:
                print(f"⚠️ Error procesando item en {sitio}: {e}")

        return noticias[::-1]  # Orden inverso

    except Exception as e:
        print(f"❌ Error al obtener noticias de {sitio}: {e}")
        return []

# Obtener detalle de noticia
async def obtener_detalle_noticia(config: dict, url: str):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
        
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
        except requests.RequestException:
            amp_url = f"{url}?amp"
            resp = requests.get(amp_url, headers=headers, timeout=15)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Extraer texto
        parrafos = [p.get_text(strip=True) for p in soup.select(config["detalle"]["texto"]) if p.get_text(strip=True)]
        texto = "\n\n".join(parrafos[:5])  # Limitar a 5 párrafos
        
        # Extraer imagen
        imagen_tag = soup.select_one(config["detalle"]["imagen"])
        imagen = imagen_tag['src'] if imagen_tag and imagen_tag.get('src') else None

        return texto, imagen

    except Exception as e:
        print(f"❌ Error en detalle de {url}: {e}")
        return None, None

# Enviar noticias
async def enviar_noticias():
    await bot.send_message(chat_id=CHAT_ID, text="🤖 Bot de noticias multi-fuente activado")
    
    while True:
        try:
            for sitio in SITIOS:
                print(f"\n🔍 Escaneando {sitio}...")
                noticias = obtener_noticias(sitio)
                nuevas = 0

                for noticia in noticias:
                    clave = canon(noticia["enlace"])
                    if clave in enviados:
                        continue

                    texto, img_detalle = await obtener_detalle_noticia(SITIOS[noticia["sitio"]], noticia["enlace"])
                    if not texto:
                        continue

                    # Construir mensaje
                    mensaje_corto = f"📰 <b>{noticia['titulo']}</b>\n🌐 <i>{noticia['sitio']}</i>\n🔗 <a href='{noticia['enlace']}'>Leer completa</a>"
                    mensaje_largo = f"📰 <b>{noticia['titulo']}</b>\n🌐 <i>{noticia['sitio']}</i>\n\n{texto[:800]}...\n\n🔗 <a href='{noticia['enlace']}'>Continuar leyendo</a>"
                    imagen = img_detalle or noticia["imagen"]

                    try:
                        if imagen:
                            await bot.send_photo(
                                chat_id=CHAT_ID,
                                photo=imagen,
                                caption=mensaje_corto,
                                parse_mode="HTML"
                            )
                            await asyncio.sleep(2)
                        
                        await bot.send_message(
                            chat_id=CHAT_ID,
                            text=mensaje_largo,
                            parse_mode="HTML",
                            disable_web_page_preview=bool(imagen)
                        )
                        
                        enviados.add(clave)
                        nuevas += 1
                        await asyncio.sleep(5)
                    
                    except TelegramError as e:
                        print(f"⚠️ Error al enviar noticia: {e}")

                print(f"✅ {sitio}: {nuevas} nuevas | Total enviados: {len(enviados)}")
            
            print(f"\n⏳ Esperando 10 minutos...")
            await asyncio.sleep(600)

        except Exception as e:
            print(f"🔥 Error crítico: {e}")
            await asyncio.sleep(60)

# Servidor Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Bot multi-fuente funcionando"

def run_server():
    app.run(host='0.0.0.0', port=8080)

def start_flask():
    threading.Thread(target=run_server, daemon=True).start()

if __name__ == "__main__":
    start_flask()
    print("🚀 Servidor iniciado")
    asyncio.run(enviar_noticias())