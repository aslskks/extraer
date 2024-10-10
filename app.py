# Ruta del archivo: /ruta/a/tu/archivo/app.py
from flask import Flask, jsonify, request
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

app = Flask(__name__)

# Definimos un User-Agent para evitar que algunas páginas bloqueen las solicitudes.
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36'
}

def download_file(url, folder):
    """Descarga un archivo desde una URL y lo guarda en la carpeta especificada."""
    try:
        response = requests.get(url, headers=HEADERS, stream=True)
        response.raise_for_status()

        # Extraer el nombre del archivo de la URL
        filename = os.path.join(folder, os.path.basename(urlparse(url).path))
        
        # Guardar el archivo en la carpeta
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)

        print(f"Archivo descargado: {filename}")
        return filename
    except requests.exceptions.RequestException as e:
        print(f"Error al descargar {url}: {e}")
        return None

def download_iframe_content(iframe_url, folder):
    """Descarga el contenido y los recursos de un iframe."""
    try:
        response = requests.get(iframe_url, headers=HEADERS)
        response.raise_for_status()
        
        # Guardar el contenido HTML del iframe
        iframe_html = response.text
        soup = BeautifulSoup(iframe_html, 'html.parser')

        # Ajustamos las URLs de los recursos en el iframe para que sean locales
        adjust_and_download_resources(soup, iframe_url, folder)

        iframe_filename = os.path.join(folder, f"iframe_{os.path.basename(urlparse(iframe_url).path)}.html")
        with open(iframe_filename, 'w', encoding='utf-8') as f:
            f.write(str(soup))

        print(f"Contenido del iframe guardado: {iframe_filename}")

    except requests.exceptions.RequestException as e:
        print(f"Error al descargar contenido del iframe {iframe_url}: {e}")

def adjust_and_download_resources(soup, base_url, folder):
    """Ajusta las rutas de los recursos en el HTML para que sean relativas y descarga los recursos."""
    # Descargar y ajustar hojas de estilo CSS
    for link in soup.find_all('link', rel='stylesheet'):
        css_url = urljoin(base_url, link.get('href'))
        local_path = download_file(css_url, folder)
        if local_path:
            link['href'] = os.path.basename(local_path)  # Cambia a la ruta local

    # Descargar y ajustar archivos JavaScript
    for script in soup.find_all('script', src=True):
        js_url = urljoin(base_url, script.get('src'))
        local_path = download_file(js_url, folder)
        if local_path:
            script['src'] = os.path.basename(local_path)  # Cambia a la ruta local

    # Descargar y ajustar imágenes
    for img in soup.find_all('img', src=True):
        img_url = urljoin(base_url, img.get('src'))
        local_path = download_file(img_url, folder)
        if local_path:
            img['src'] = os.path.basename(local_path)  # Cambia a la ruta local

@app.route('/get_resources', methods=['GET'])
def get_resources():
    url = request.args.get('url')
    folder_name = request.args.get('folder_name', 'website_content')  # Nombre de la carpeta por defecto

    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    # Crea la carpeta de destino si no existe
    os.makedirs(folder_name, exist_ok=True)

    try:
        # Hacemos la solicitud GET al sitio web
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        
        # Extraemos el HTML de la página
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')

        # Ajustamos las URLs de los recursos para que sean locales
        adjust_and_download_resources(soup, url, folder_name)

        # Guardamos el HTML de la página principal
        html_filename = os.path.join(folder_name, 'index.html')
        with open(html_filename, 'w', encoding='utf-8') as f:
            f.write(str(soup))

        # Descargar contenido de iframes
        for iframe in soup.find_all('iframe', src=True):
            iframe_url = urljoin(url, iframe.get('src'))
            download_iframe_content(iframe_url, folder_name)

        return jsonify({'message': f'Contenido descargado en la carpeta {folder_name}'})

    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
