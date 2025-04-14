import requests
from bs4 import BeautifulSoup
import asyncio
from telegram import Bot
from telegram.error import TelegramError
import threading
from flask import Flask
import os
from urllib.parse import urlsplit, urlunsplit
from datetime import datetime
from telegram.request import AsyncHTTPXRequest


# Configuración
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
URL = "https://larepublica.pe/espectaculos"

if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("❌ Faltan variables de entorno BOT_TOKEN o CHAT_ID")

bot = Bot(token=BOT_TOKEN, request=AsyncHTTPXRequest())

enviados = set()

# Helper para URLs canónicas
def canon(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))

# Obtener noticias
def obtener_noticias():
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        response = requests.get(URL, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        noticias = []
        contenedor = soup.find('div', class_="ListSection_list__Ew_UF")

        if not contenedor:
            print("❌ No se encontró el contenedor de noticias")
            return noticias

        items = contenedor.find_all('div', class_=lambda x: x and "ListSection_list__section--item__zeP_z" in x)

        for item in items:
            img_tag = item.find('img')
            imagen = img_tag['src'] if img_tag and 'src' in img_tag.attrs else None
            
            h2_tag = item.find('h2')
            if not h2_tag:
                continue

            link_tag = h2_tag.find('a')
            if not link_tag:
                continue

            titulo = link_tag.get_text(strip=True)
            enlace = link_tag.get('href', '')
            enlace_completo = f"https://larepublica.pe{enlace}" if enlace.startswith('/') else enlace
            
            if titulo and enlace_completo:
                noticias.append((titulo, enlace_completo, imagen))

        return noticias[::-1]  # Orden inverso (más nuevas primero)

    except Exception as e:
        print(f"❌ Error al obtener noticias: {e}")
        return []

# Obtener detalle de noticia
async def obtener_detalle_noticia(url: str):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
        amp_url = f"{url}?outputType=amp"
        
        try:
            resp = requests.get(amp_url, headers=headers, timeout=10)
            resp.raise_for_status()
        except:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        parrafos = [p.get_text(strip=True) for p in soup.find_all("p") if p.get_text(strip=True)]
        texto = "\n\n".join(parrafos[:5])  # Limitar a 5 párrafos
        
        # Buscar imagen principal
        imagen = None
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if src.startswith(("https://imgmedia.larepublica.pe/", "http://imgmedia.larepublica.pe/")):
                imagen = src
                break

        return texto, imagen

    except Exception as e:
        print(f"❌ Error en detalle de {url}: {e}")
        return None, None

# Enviar noticias
async def enviar_noticias():
    await bot.send_message(chat_id=CHAT_ID, text="🤖 Bot de noticias activado - Monitoreando La República...")
    
    while True:
        try:
            noticias = obtener_noticias()
            nuevas = 0

            for titulo, enlace, img_prev in noticias:
                clave = canon(enlace)
                if clave in enviados:
                    continue

                texto, img_detalle = await obtener_detalle_noticia(enlace)
                if not texto:
                    continue

                # Mensaje optimizado para límites de Telegram
                mensaje_corto = f"📢 <b>{titulo}</b>\n\n🔗 <a href='{enlace}'>Leer noticia completa</a>"
                mensaje_largo = f"📢 <b>{titulo}</b>\n\n{texto[:1000]}...\n\n🔗 <a href='{enlace}'>Leer más</a>"
                imagen = img_detalle or img_prev

                try:
                    if imagen:
                        # Primero envía la imagen con caption corto
                        await bot.send_photo(
                            chat_id=CHAT_ID,
                            photo=imagen,
                            caption=mensaje_corto,  # Límite: 1024 caracteres
                            parse_mode="HTML"
                        )
                        # Luego envía el texto completo como mensaje separado
                        await bot.send_message(
                            chat_id=CHAT_ID,
                            text=mensaje_largo,
                            parse_mode="HTML",
                            disable_web_page_preview=True
                        )
                    else:
                        await bot.send_message(
                            chat_id=CHAT_ID,
                            text=mensaje_largo,
                            parse_mode="HTML",
                            disable_web_page_preview=True
                        )
                    
                    enviados.add(clave)
                    nuevas += 1
                    await asyncio.sleep(5)  # Espera entre envíos
                
                except TelegramError as e:
                    print(f"⚠️ Error al enviar: {e}")

            if nuevas == 0:
                print(f"{datetime.now().isoformat()} - No hay noticias nuevas")
            
            await asyncio.sleep(600)  # Espera 10 minutos entre ciclos

        except Exception as e:
            print(f"🔥 Error crítico: {e}")
            await asyncio.sleep(60)

# Servidor Flask para mantener activo
app = Flask(__name__)

@app.route('/')
def home():
    return "🔍 Bot de noticias funcionando correctamente"

def run_server():
    app.run(host='0.0.0.0', port=8080)

def start_flask():
    threading.Thread(target=run_server, daemon=True).start()

# Inicio
if __name__ == "__main__":
    start_flask()
    print("🚀 Servidor Flask iniciado")
    asyncio.run(enviar_noticias())