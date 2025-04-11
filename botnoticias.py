import requests
from bs4 import BeautifulSoup
import asyncio
from telegram import Bot
import threading
from flask import Flask
import os
from urllib.parse import urlsplit, urlunsplit

# Configura tu bot de Telegram oficial
bot_token = os.getenv('BOT_TOKEN')
chat_id = os.getenv('CHAT_ID')

if not bot_token or not chat_id:
    raise ValueError("❌ BOT_TOKEN o CHAT_ID no están definidos en las variables de entorno.")

bot = Bot(token=bot_token)

# URL de la página de espectáculos
URL = "https://larepublica.pe/espectaculos"

# Lista para guardar los títulos ya enviados
enviados: set[str] = set() 

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
        return noticias[::-1]

    except Exception as e:
        print(f"❌ Error obteniendo noticias: {e}")
        return []



def obtener_detalle_noticia(url: str):
    """Devuelve (texto, imagen) del cuerpo de la noticia."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
    }
    # 1) Probamos la página AMP, que siempre trae el artículo completo
    amp_url = f"{url}?outputType=amp"

    try:
        resp = requests.get(amp_url, headers=headers, timeout=10)
        resp.raise_for_status()
    except requests.HTTPError:
        # Fallback a la URL original por si la AMP falla
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # El cuerpo de la nota en AMP está dentro de <div class="paragraph"> o simplemente <p>
    parrafos = [p.get_text(strip=True) for p in soup.find_all("p") if p.get_text(strip=True)]
    texto = "\n\n".join(parrafos)

    # Primera imagen válida
    imagen = None
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if src.startswith("https://imgmedia.larepublica.pe/"):
            imagen = src
            break

    return texto, imagen


def canon(url: str) -> str:
    """Devuelve la URL sin query ni fragmento: https://ejemplo.com/pag → misma clave siempre."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))

enviados: set[str] = set()          # vive en RAM; suficiente mientras el contenedor no se reinicie


async def enviar_noticias():
    await bot.send_message(chat_id=chat_id,
                           text="✅ Bot de noticias iniciado y escuchando novedades…")

    while True:
        noticias = obtener_noticias()[::-1]
        enviadas_este_ciclo = 0       # ← contador

        for titulo, enlace, img_prev in noticias:
            clave = canon(enlace)
            if clave in enviados:
                continue

            # ---------- envío ----------
            try:
                texto, img_detalle = obtener_detalle_noticia(enlace)
                mensaje = f"📰 {titulo}\n\n{texto}\n\n🔗 {enlace}"
                imagen = img_detalle or img_prev

                if imagen and imagen.startswith("http"):
                    await bot.send_photo(chat_id=chat_id,
                                         photo=imagen,
                                         caption=mensaje[:1024])
                else:
                    await bot.send_message(chat_id=chat_id,
                                           text=mensaje[:4096])

                enviados.add(clave)
                enviadas_este_ciclo += 1          # ← incrementa
            except Exception as e:
                print(f"Error enviando noticia: {e}")

        # ---------- aviso si no se envió nada ----------
        if enviadas_este_ciclo == 0:
            await bot.send_message(chat_id=chat_id,
                                   text="⚠️ Sin noticias nuevas en La República.")

        print("⏳ Esperando 10 minutos…")
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
