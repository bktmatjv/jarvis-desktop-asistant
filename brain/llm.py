from groq import Groq
import os
from dotenv import load_dotenv
from pathlib import Path


base_dir = Path(__file__).resolve().parent.parent
env_path = base_dir / '.env'

# Carga las variables del archivo .env
load_dotenv(dotenv_path=env_path)

api_keyy = os.getenv("GROQ_API_KEY")

'''
    script usado para comunicarte con el modelo de lenguaje de Groq, enviándole prompts y recibiendo respuestas. La idea es que esta función sea la interfaz principal entre tu cerebro de Jarvis y el LLM, para que cada vez que necesites interpretar una orden del usuario o tomar una decisión basada en lenguaje natural, puedas enviarle un prompt a esta función, y ella se encargue de comunicarse con Groq y devolverte la respuesta del modelo. AUN EN DESARROLLO, NO TODAS LAS FUNCIONES ESTÁN OPTIMIZADAS O TERMINADAS, PERO LA IDEA ES QUE SEA UNA HERRAMIENTA COMPLETA PARA INTERACTUAR CON EL LLM DESDE EL CEREBRO DE JARVIS.
    informacion:
    - El modelo que estamos usando es "llama-3.1-8b-instant", que es un modelo optimizado para respuestas rápidas y con buena comprensión de instrucciones.
    - La función ask_llm toma un string como prompt, lo envía a Groq, y devuelve la respuesta del modelo como string.
    - En el futuro, podríamos expandir esta función para manejar diferentes tipos de prompts,
        como prompts de planificación, prompts de generación de código, o incluso prompts para interactuar con la memoria, dependiendo de las necesidades del cerebro de Jarvis.
'''

# coloca tu API key aquí
client = Groq(
    # en este apartado pones tu api key de groq, que debe estar guardada en tu archivo .env como GROQ_API_KEY=tu_clave_aqui
    api_key=api_keyy
)

# modelo escogido para las interacciones con el LLM, puedes cambiarlo por otro modelo de Groq si lo deseas, pero "llama-3.1-8b-instant" es una buena opción para empezar por su equilibrio entre velocidad y capacidad de comprensión.
MODEL = "llama-3.1-8b-instant"


# función principal para enviar prompts al LLM y recibir respuestas
def ask_llm(prompt: str) -> str:
    try:
        chat = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model=MODEL,
            temperature=0.2,
            max_tokens=200
        )

        return chat.choices[0].message.content
    
    except Exception as e:
        print("LLM ERROR:", e)
        return ""