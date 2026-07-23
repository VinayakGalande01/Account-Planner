"""
LOGGING CONFIGURATION (logging_config.py)
Sets up structured file and console logging across backend components:
database, backend, auth, llm, pipeline, and frontend operations with rotation.
"""

# --- SECTION 1: Log Directory Setup & Imports ---
# Creates local 'logs/' directory if absent and loads standard logging modules.
import logging.config
import os

LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

# --- SECTION 2: Rotating File & Console Handlers ---
# Defines dictConfig handlers with 10MB file rotation limits and standard formatting.
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
        "pipeline_file": {
            "level": "INFO",
            "formatter": "standard",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOGS_DIR, "pipeline.log"),
            "maxBytes": 10485760,
            "backupCount": 5,
        },
    },
    "loggers": {
        "pipeline": {
            "handlers": ["console", "pipeline_file"],
            "level": "INFO",
            "propagate": False,
        },
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

# --- SECTION 3: Logging Initialization Entrypoint ---
# Applies the dictConfig structure to Python's logging system.
def setup_logging():
    logging.config.dictConfig(LOGGING_CONFIG)

