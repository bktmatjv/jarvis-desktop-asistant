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
            
        query = params.get("query", "")
        max_results = params.get("max_results", 5)
        
        if not query:
            print("Error: query vacía.")
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
        
        try:
            response = tavily_client.search(query=query, search_depth="basic", max_results=max_results)
            results = response.get("results", [])
        except Exception as e:
            print(f"Error en la búsqueda con Tavily: {e}")
            traceback.print_exc()
            return

        if not results:
            print(f"No se encontraron resultados para: {query}")
        else:
            formatted_results = []
            for r in results:
                title = r.get("title", "Sin título")
                url = r.get("url", "")
                content = r.get("content", "")
                formatted_results.append(f"[{title}]({url}): {content}")
            
            print(f"Resultados de búsqueda para '{query}':\n" + "\n".join(formatted_results))
            
    except Exception as e:
        print(f"Error en web_search: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
