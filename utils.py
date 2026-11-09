#!/usr/bin/env python3
"""
Utility functions for RegisV8
"""

import random
import string
import re
from typing import Optional
from urllib.parse import urlparse


def validate_url(url: str) -> bool:
    """
    Validate URL format
    
    Args:
        url: URL to validate
        
    Returns:
        True if URL is valid
    """
    if not url:
        return False
    
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


def validate_email(email: str) -> bool:
    """
    Validate email format
    
    Args:
        email: Email to validate
        
    Returns:
        True if email is valid
    """
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def generate_random_string(
    length: int = 10,
    include_digits: bool = True,
    include_special: bool = False
) -> str:
    """
    Generate random string
    
    Args:
        length: String length
        include_digits: Include digits
        include_special: Include special characters
        
    Returns:
        Random string
    """
    chars = string.ascii_letters
    
    if include_digits:
        chars += string.digits
    
    if include_special:
        chars += string.punctuation
    
    return ''.join(random.choice(chars) for _ in range(length))


def generate_random_number(length: int = 10) -> str:
    """
    Generate random number string
    
    Args:
        length: Number length
        
    Returns:
        Random number string
    """
    return ''.join(random.choice(string.digits) for _ in range(length))


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe file operations
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip('. ')
    return sanitized


def truncate_string(text: str, max_length: int = 100) -> str:
    """
    Truncate string to max length with ellipsis
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        
    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + "..."


def safe_json_parse(json_str: str) -> Optional[dict]:
    """
    Safely parse JSON string
    
    Args:
        json_str: JSON string
        
    Returns:
        Parsed JSON or None if invalid
    """
    import json
    
    try:
        return json.loads(json_str)
    except:
        return None


def extract_domain(url: str) -> str:
    """
    Extract domain from URL
    
    Args:
        url: Full URL
        
    Returns:
        Domain string
    """
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except:
        return ""
