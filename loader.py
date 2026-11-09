#!/usr/bin/env python3
"""
Loader module for RegisV8
Handles reading and parsing of input files (links and accounts)
"""

from typing import List, Tuple

from .models import Site, Account


def load_sites(file_path: str) -> List[Site]:
    """
    Load target sites from file
    
    Format: One URL per line, empty lines are ignored
    
    Args:
        file_path: Path to file containing URLs
        
    Returns:
        List of Site objects
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file is empty or contains invalid data
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        raise FileNotFoundError(f"Sites file not found: {file_path}")
    
    if not urls:
        raise ValueError(f"No URLs found in file: {file_path}")
    
    sites = []
    for url in urls:
        site = Site(url=url)
        if not site.is_valid():
            raise ValueError(f"Invalid URL format: {url}")
        sites.append(site)
    
    return sites


def load_accounts(file_path: str) -> List[Account]:
    """
    Load accounts from file
    
    Format (6 fields separated by |):
    username|password|fullname|banktype|bankname|banknumber
    
    Example:
    user01|password01|Andi Saputra|59|GOPAY|08123456789
    user02|password02|Budi Santoso|60|DANA|08123456790
    
    Field descriptions:
    1. username   - Username untuk registrasi
    2. password   - Password untuk registrasi
    3. fullname   - Nama lengkap user (sekaligus bank holder)
    4. banktype   - ID tipe bank dari HTML site (59, 60, etc)
    5. bankname   - Nama bank (GOPAY, DANA, etc)
    6. banknumber - Nomor rekening bank
    
    Args:
        file_path: Path to file containing accounts
        
    Returns:
        List of Account objects
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file is empty or contains invalid data
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        raise FileNotFoundError(f"Accounts file not found: {file_path}")
    
    if not lines:
        raise ValueError(f"No accounts found in file: {file_path}")
    
    accounts = []
    for line_num, line in enumerate(lines, 1):
        parts = line.split('|')
        
        if len(parts) != 6:
            raise ValueError(
                f"Invalid account format at line {line_num}. "
                f"Expected 6 fields separated by '|', got {len(parts)}\n"
                f"Format: username|password|fullname|banktype|bankname|banknumber\n"
                f"Line: {line}\n"
                f"Fields found ({len(parts)}): {parts}"
            )
        
        username = parts[0].strip()
        password = parts[1].strip()
        fullname = parts[2].strip()
        bank_type = parts[3].strip()
        bank_name = parts[4].strip()
        bank_number = parts[5].strip()
        
        missing_fields = []
        if not username:
            missing_fields.append("username (field 1)")
        if not password:
            missing_fields.append("password (field 2)")
        if not fullname:
            missing_fields.append("fullname (field 3)")
        if not bank_type:
            missing_fields.append("banktype (field 4)")
        if not bank_name:
            missing_fields.append("bankname (field 5)")
        if not bank_number:
            missing_fields.append("banknumber (field 6)")
        
        if missing_fields:
            raise ValueError(
                f"Invalid account at line {line_num}. "
                f"Missing required fields: {', '.join(missing_fields)}\n"
                f"Line: {line}"
            )
        
        if not bank_type.isdigit():
            print(f"⚠️  [WARNING] Line {line_num}: banktype '{bank_type}' is not numeric. "
                  f"Expected numeric ID from site HTML (e.g., '59')")
        
        account = Account(
            username=username,
            password=password,
            fullname=fullname,
            bank_type=bank_type,
            bank_name=bank_name,
            bank_number=bank_number
        )
        
        if not account.is_valid():
            raise ValueError(f"Invalid account data at line {line_num}")
        
        accounts.append(account)
    
    return accounts


def load_progress(output_folder: str) -> Tuple[int, int]:
    """
    Load progress from previous run
    
    Args:
        output_folder: Path to output folder
        
    Returns:
        Tuple of (last_site_index, last_account_index)
    """
    import os
    import json
    
    progress_file = os.path.join(output_folder, 'progress.json')
    
    if not os.path.exists(progress_file):
        return (0, 0)
    
    try:
        with open(progress_file, 'r', encoding='utf-8') as f:
            progress = json.load(f)
        
        last_site = progress.get('last_site', 0)
        last_account = progress.get('last_account', 0)
        
        return (last_site, last_account)
    except:
        return (0, 0)


def save_progress(output_folder: str, site_index: int, account_index: int):
    """
    Save current progress
    
    Args:
        output_folder: Path to output folder
        site_index: Current site index
        account_index: Current account index
    """
    import os
    import json
    
    os.makedirs(output_folder, exist_ok=True)
    
    progress_file = os.path.join(output_folder, 'progress.json')
    
    progress = {
        'last_site': site_index,
        'last_account': account_index
    }
    
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump(progress, f, indent=2)


def validate_accounts_file(file_path: str) -> Tuple[bool, List[str]]:
    """
    Validate accounts.txt file without loading all accounts
    
    Args:
        file_path: Path to accounts file
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return False, [f"File not found: {file_path}"]
    
    if not lines:
        return False, ["File is empty"]
    
    for line_num, line in enumerate(lines, 1):
        parts = line.split('|')
        
        if len(parts) != 6:
            errors.append(
                f"Line {line_num}: Expected 6 fields, got {len(parts)}"
            )
            continue
        
        username = parts[0].strip()
        password = parts[1].strip()
        fullname = parts[2].strip()
        bank_type = parts[3].strip()
        bank_name = parts[4].strip()
        bank_number = parts[5].strip()
        
        if not username:
            errors.append(f"Line {line_num}: username (field 1) is empty")
        if not password:
            errors.append(f"Line {line_num}: password (field 2) is empty")
        if not fullname:
            errors.append(f"Line {line_num}: fullname (field 3) is empty")
        if not bank_type:
            errors.append(f"Line {line_num}: banktype (field 4) is empty")
        elif not bank_type.isdigit():
            errors.append(
                f"Line {line_num}: banktype '{bank_type}' is not numeric"
            )
        if not bank_name:
            errors.append(f"Line {line_num}: bankname (field 5) is empty")
        if not bank_number:
            errors.append(f"Line {line_num}: banknumber (field 6) is empty")
    
    return len(errors) == 0, errors
