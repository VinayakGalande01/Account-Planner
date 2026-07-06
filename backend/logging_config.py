import logging.config
import os

LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "formatter": "standard",
            "class": "logging.StreamHandler",
        },
        "database_file": {
            "level": "INFO",
            "formatter": "standard",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOGS_DIR, "database.log"),
            "maxBytes": 10485760, # 10MB
            "backupCount": 5,
        },
        "backend_file": {
            "level": "INFO",
            "formatter": "standard",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOGS_DIR, "backend.log"),
            "maxBytes": 10485760,
            "backupCount": 5,
        },
        "auth_file": {
            "level": "INFO",
            "formatter": "standard",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOGS_DIR, "auth.log"),
            "maxBytes": 10485760,
            "backupCount": 5,
        },
        "llm_file": {
            "level": "INFO",
            "formatter": "standard",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOGS_DIR, "llm.log"),
            "maxBytes": 10485760,
            "backupCount": 5,
        },
        "frontend_file": {
            "level": "INFO",
            "formatter": "standard",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOGS_DIR, "frontend.log"),
            "maxBytes": 10485760,
            "backupCount": 5,
        },
    },
    "loggers": {
        "database": {
            "handlers": ["console", "database_file"],
            "level": "INFO",
            "propagate": False,
        },
        "backend": {
            "handlers": ["console", "backend_file"],
            "level": "INFO",
            "propagate": False,
        },
        "auth": {
            "handlers": ["console", "auth_file"],
            "level": "INFO",
            "propagate": False,
        },
        "llm": {
            "handlers": ["console", "llm_file"],
            "level": "INFO",
            "propagate": False,
        },
        "frontend": {
            "handlers": ["console", "frontend_file"],
            "level": "INFO",
            "propagate": False,
        },
        "": {
            "handlers": ["console"],
            "level": "INFO",
        },
    }
}

def setup_logging():
    logging.config.dictConfig(LOGGING_CONFIG)
