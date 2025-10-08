# logging_config.py

import os
import sys
import json
import logging
from datetime import datetime

# Variable global para evitar mensajes duplicados
_environment_logged = False

def is_cloud_run():
    """Detecta si estamos en Cloud Run"""
    global _environment_logged
    
    scope = os.environ.get("SCOPE", "development").lower()
    is_cloud = scope == "prod"

    env_type = f"Cloud Run (SCOPE = {scope})" if is_cloud else f"Local (SCOPE = {scope})"
    
    # Mostrar solo la primera vez
    if not _environment_logged:
        sys.stderr.write(f"Entorno encontrado: {env_type}\n")
        sys.stderr.flush()
        _environment_logged = True
    
    return is_cloud

class SmartFormatter(logging.Formatter):
    """
    Formatter inteligente que:
    - En Cloud Run: Genera JSON estructurado con severity
    - En Local: Muestra logs normales legibles
    """
    
    SEVERITY_MAPPING = {
        'DEBUG': 'DEBUG',
        'INFO': 'INFO',
        'WARNING': 'WARNING',
        'ERROR': 'ERROR',
        'CRITICAL': 'CRITICAL'
    }
    
    def __init__(self):
        super().__init__()
        self.use_json = is_cloud_run()
    
    def format(self, record):
        if self.use_json:
            # Cloud Run: JSON con severity
            log_entry = {
                'severity': self.SEVERITY_MAPPING.get(record.levelname, 'INFO'),
                'message': record.getMessage(),
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'logger': record.name,
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno
            }
            
            if record.exc_info:
                log_entry['exception'] = self.formatException(record.exc_info)
            
            return json.dumps(log_entry, ensure_ascii=False)
        else:
            # Local: Formato legible CON timestamp
            timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
            return f"{timestamp} - {record.levelname} - {record.name} - {record.getMessage()}"

def configure_logging():
    """Configura el logging automáticamente para todo el proyecto"""
    
    # Obtener el root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Limpiar handlers existentes
    root_logger.handlers.clear()
    
    # Configurar handler con el formatter inteligente
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(SmartFormatter())
    handler.setLevel(logging.INFO)
    handler.flush = sys.stdout.flush
    
    root_logger.addHandler(handler)