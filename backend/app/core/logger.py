import os
import logging
from logging.handlers import RotatingFileHandler

def get_logger(name="jarvis_backend"):
    # Directorio base del backend
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(os.path.dirname(current_dir))
    logs_dir = os.path.join(base_dir, "logs")
    
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
        
    log_file = os.path.join(logs_dir, "error.log")
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.ERROR)
    
    # Evitar duplicar handlers si se llama varias veces
    if not logger.handlers:
        # Handler para el archivo rotativo (10MB max, guarda 5 respaldos)
        file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
        file_handler.setLevel(logging.ERROR)
        
        # Handler para la consola
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.ERROR)
        
        # Formato detallado
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
    return logger
