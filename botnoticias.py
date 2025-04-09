import requests
from bs4 import BeautifulSoup
import asyncio
from telegram import Bot
import threading
from flask import Flask

# Configura tu bot de Telegram
bot_token = '8182687940:AAEgkQzqWTV2WH7AQzxNhorO7Bfq6LNsSAI'
chat_id = '5703458157'
bot = Bot(token=bot_token)

# URL de la página de espectáculos
URL = "https://larepublica.pe/espectaculos"

# Lista para guardar los títulos ya enviados
enviados = set()

def obtener_noticias():
    """Obtiene la lista de noticias de la página principal."""
    try:
        response = requests.get(URL)
        soup = BeautifulSoup(response.text, 'html.parser')

        noticias = []

        # Buscar todos los enlaces de las noticias
        for link in soup.find_all('a', class_="extend-link"):
            titulo = link.get_text(strip=True)
            enlace = link.get('href')
            enlace_completo = f"https://larepublica.pe{enlace}" if enlace.startswith('/') else enlace

            noticias.append((titulo, enlace_completo))

        print(f"Encontradas {len(noticias)} noticias")
        return noticias

    except Exception as e:
        print(f"Error obteniendo noticias: {e}")
        return []

def obtener_detalle_noticia(url):
    """Ingresa al detalle de la noticia y extrae texto e imagen."""
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extraer contenido principal
        contenido = []
        for parrafo in soup.find_all('p'):
            texto = parrafo.get_text(strip=True)
            if texto:
                contenido.append(texto)

        texto_completo = "\n\n".join(contenido)

        # Buscar imagen principal del dominio correcto
        imagen = None
        for img_tag in soup.find_all('img'):
            src = img_tag.get('src')
            if src and src.startswith('https://imgmedia.larepublica.pe/'):
                imagen = src
                break

        return texto_completo, imagen

    except Exception as e:
        print(f"Error al obtener detalle de noticia: {e}")
        return "", None

async def enviar_noticias():
    """Revisa y envía noticias nuevas."""
    while True:
        noticias = obtener_noticias()

        if len(noticias) == 0:
            try:
                await bot.send_message(chat_id=chat_id, text="⚠️ No se encontraron noticias en La República.")
                print("⚠️ Aviso enviado: No se encontraron noticias.")
            except Exception as e:
                print(f"Error enviando aviso de noticias vacías: {e}")

        for titulo, enlace in noticias:
            if titulo not in enviados:
                try:
                    texto_completo, imagen = obtener_detalle_noticia(enlace)

                    if not texto_completo:
                        texto_completo = "No se pudo extraer el contenido completo."

                    mensaje = f"📰 {titulo}\n\n{texto_completo}\n\n🔗 {enlace}"

                    if imagen and imagen.startswith("http"):
                        await bot.send_photo(chat_id=chat_id, photo=imagen, caption=mensaje[:1024])
                        print(f"✅ Enviada noticia con imagen: {titulo}")
                    else:
                        await bot.send_message(chat_id=chat_id, text=mensaje[:4096])
                        print(f"✅ Enviada noticia sin imagen: {titulo}")

                    enviados.add(titulo)

                except Exception as e:
                    print(f"Error enviando noticia: {e}")

        print("⏳ Esperando 10 minutos para la siguiente revisión...")
        await asyncio.sleep(600)

# Servidor Flask para mantener Replit vivo
app = Flask('')

@app.route('/')
def home():
    return "Bot de noticias activo!"

def run_server():
    app.run(host='0.0.0.0', port=8080)

def start_flask():
    threading.Thread(target=run_server).start()

if __name__ == "__main__":
    start_flask()
    asyncio.run(enviar_noticias())
