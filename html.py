import requests
from bs4 import BeautifulSoup

URL = "https://larepublica.pe/espectaculos"

def ver_html():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    response = requests.get(URL, headers=headers)

    if response.status_code == 200:
        print("✅ Página descargada correctamente.")
        html = response.text

        # Corta solo los primeros 2000 caracteres para no saturar la consola
        print("\n--- HTML (primeros 2000 caracteres) ---\n")
        print(html[:2000])

        # Buscar si existe el contenedor
        soup = BeautifulSoup(html, 'html.parser')
        contenedor = soup.find('div', class_="ListSection_list__Ew_UF")
        
        if contenedor:
            print("\n✅ Contenedor encontrado: 'ListSection_list__Ew_UF'")
        else:
            print("\n❌ No se encontró el contenedor 'ListSection_list__Ew_UF'.")
    else:
        print(f"⚠️ Error: Código de estado {response.status_code}")

if __name__ == "__main__":
    ver_html()
