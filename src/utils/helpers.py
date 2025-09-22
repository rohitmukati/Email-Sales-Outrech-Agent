import os
import json
import yaml
import logging
from typing import Any

def setup_logging(log_file: str = "app.log"):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def load_json(path: str, default=None) -> Any:
    if os.path.exists(path):
        try:
            if os.path.getsize(path) == 0:
                return default if default is not None else []
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading {path}: {e}")
            return default if default is not None else []
    return default if default is not None else []

def save_json(path: str, data: Any):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Error saving {path}: {e}")

def load_config(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logging.error(f"Error loading config {path}: {e}")
        return {}

def upsert_draft(drafts: list, new_draft: dict) -> list:
    # Always replace with only the new draft (no multiple drafts)
    return [new_draft]
