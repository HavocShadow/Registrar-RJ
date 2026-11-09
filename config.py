#!/usr/bin/env python3
"""
Configuration module for RegisV8
Reads and manages all configuration from config.json
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Union

from .models import Config


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_config(
    config_path: Union[str, os.PathLike[str]] = PROJECT_ROOT / "config.json",
) -> Config:
    """
    Load configuration from JSON file
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Config object with all settings
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If config file is invalid JSON
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = json.load(f)
    
    return Config(
        timeout=config_data.get('timeout', 15),
        retry=config_data.get('retry', 3),
        concurrency=config_data.get('concurrency', 30),
        user_agent=config_data.get('user_agent', 'Mozilla/5.0'),
        delay=config_data.get('delay', 0),
        output_folder=config_data.get('output_folder', 'output'),
        max_redirects=config_data.get('max_redirects', 5),
        ssl_verify=config_data.get('ssl_verify', False)
    )
