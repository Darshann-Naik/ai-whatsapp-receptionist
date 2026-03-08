import logging
import sys
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """
    Custom formatter to output logs as JSON.
    Crucial for production monitoring and debugging.
    """
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage(),
        }
        # Include 'extra' fields (like tenant_id, phone_number) if they exist
        if hasattr(record, "extra_info"):
            log_record.update(record.extra_info)
        
        # Capture exception info if available
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_record)

def setup_logging():
    logger = logging.getLogger("app")
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate logs if setup_logging is called twice
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        
    return logger

# Singleton instance for the app
logger = setup_logging()