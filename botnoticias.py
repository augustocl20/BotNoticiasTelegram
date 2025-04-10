import requests
from bs4 import BeautifulSoup
import asyncio
from telegram import Bot
import threading
from flask import Flask

# Configura tu bot de Telegram
bot_token = '8182687940:AAEgkQzqWTV2WH7AQzxNhorO7Bfq6LNsSAI'
chat_id = '5703458157'

# Configura tu bot de Telegram
#bot_token = '7678601013:AAEyspczh_FLXE13A-2upBD6HngO0acAFXE'
#chat_id = '5703458157'

bot = Bot(token=bot_token)

# URL de la página de espectáculos
URL = "https://larepublica.pe/espectaculos"

# Lista para guardar los títulos ya enviados
enviados = set()

def obtener_noticias():
    """Obtiene la lista de noticias principales (corregido final)."""
    try:
        print("🔵 Iniciando obtención de noticias...")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        response = requests.get(URL, headers=headers)
        print("🟢 Página descargada correctamente.")

        soup = BeautifulSoup(response.text, 'html.parser')
        print("🟢 HTML parseado con BeautifulSoup.")

        noticias = []

        contenedor = soup.find('div', class_="ListSection_list__Ew_UF")
        if not contenedor:
            print("❌ No se encontró el contenedor principal de noticias.")
            return noticias

        print("🟢 Contenedor de noticias encontrado.")

        items = contenedor.find_all('div', attrs={"class": lambda x: x and "ListSection_list__section--item__zeP_z extend-link--outside" in x})
        print(f"🔵 Encontrados {len(items)} items de noticias.")

        if not items:
            print("⚠️ No hay noticias nuevas para procesar.")
            return noticias

        for idx, item in enumerate(items):
            print(f"🔵 Procesando noticia {idx+1}...")

            # Buscar imagen
            img_tag = item.find('img')
            imagen = img_tag['src'] if img_tag and img_tag.get('src') else None

            # Buscar título y enlace
            h2_tag = item.find('h2')
            if not h2_tag:
                print(f"⚠️ No se encontró el h2 en noticia {idx+1}.")
                continue

            link_tag = h2_tag.find('a')
            if not link_tag:
                print(f"⚠️ No se encontró link en noticia {idx+1}.")
                continue

            titulo = link_tag.get_text(strip=True)
            enlace = link_tag.get('href')

            if titulo and enlace:
                enlace_completo = f"https://larepublica.pe{enlace}" if enlace.startswith('/') else enlace
                noticias.append((titulo, enlace_completo, imagen))  # <<< GUARDAMOS TAMBIÉN LA IMAGEN
                print(f"✅ Noticia agregada: {titulo}")

        print(f"🟢 Total de noticias agregadas: {len(noticias)}")
        return noticias

    except Exception as e:
        print(f"❌ Error obteniendo noticias: {e}")
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

        for titulo, enlace, imagen_preview in noticias:
            if titulo not in enviados:
                try:
                    texto_completo, imagen_detalle = obtener_detalle_noticia(enlace)

                    if not texto_completo:
                        texto_completo = "No se pudo extraer el contenido completo."

                    mensaje = f"📰 {titulo}\n\n{texto_completo}\n\n🔗 {enlace}"

                    imagen_a_enviar = imagen_detalle if imagen_detalle else imagen_preview

                    if imagen_a_enviar and imagen_a_enviar.startswith("http"):
                        await bot.send_photo(chat_id=chat_id, photo=imagen_a_enviar, caption=mensaje[:1024])
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
