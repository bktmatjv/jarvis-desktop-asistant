import sys
import json

def main():
    if len(sys.argv) < 2:
        print("Error: Se requiere la ruta del archivo JSON con los parámetros.")
        return
        
    json_path = sys.argv[1]
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            params = json.load(f)
            
        a = params.get("a", 0)
        b = params.get("b", 0)
        
        result = a + b
        print(f"El resultado de sumar {a} y {b} es: {result}")
        
    except Exception as e:
        print(f"Error en la skill: {str(e)}")

if __name__ == "__main__":
    main()
