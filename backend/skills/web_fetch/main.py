import sys
import json
import traceback

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None

def main():
    if len(sys.argv) < 2:
        print("Error: Se requiere la ruta del archivo JSON con los parámetros.")
        return
        
    json_path = sys.argv[1]
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            params = json.load(f)
            
        url = params.get("url", "")
        
        if not url:
            print("Error: url vacía.")
            return

        if TavilyClient is None:
            print("Error: La librería tavily-python no está instalada. Ejecuta 'pip install tavily-python'.")
            return

        # Añadimos la ruta base para poder importar config si se corre como script
        import os
        backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
            
        from app.core.config import settings

        api_key = settings.TAVILY_API_KEY
        if not api_key:
            print("Error: TAVILY_API_KEY no está configurada en .env")
            return

        tavily_client = TavilyClient(api_key=api_key)
        
        print(f"Obteniendo contenido de: {url} mediante Tavily Extract...")
        
        try:
            response = tavily_client.extract(urls=[url])
            results = response.get("results", [])
        except Exception as e:
            print(f"Error HTTP al acceder a la URL mediante Tavily: {e}")
            traceback.print_exc()
            return
        
        if not results:
            print("No se pudo extraer contenido válido.")
            return
            
        extracted_text = results[0].get("raw_content", "")
        
        # Ocasionalmente Tavily devuelve html crudo si no logra extraerlo
        # Podemos devolver el texto plano
        if not extracted_text:
            extracted_text = "No se encontró contenido principal."

        if len(extracted_text) > 4000:
            extracted_text = extracted_text[:4000] + "\n\n[Texto truncado. El contenido es muy largo.]"

        print(f"Contenido extraído:\n\n{extracted_text}")
            
    except Exception as e:
        print(f"Error en web_fetch: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
