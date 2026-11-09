#!/usr/bin/env python3
"""
Logger module for RegisV8
Handles all logging to files
"""

import os
import json
from typing import List

from .models import MissionResult, MissionState


class Logger:
    """File-based logger for mission results and statistics"""
    
    def __init__(self, output_folder: str = "output"):
        """
        Initialize logger
        
        Args:
            output_folder: Base folder for log files
        """
        self.output_folder = output_folder
        self._ensure_output_folder()
    
    def _ensure_output_folder(self):
        """Create output folder if it doesn't exist"""
        os.makedirs(self.output_folder, exist_ok=True)
    
    def log_success(self, result: MissionResult):
        """
        Log successful registration
        
        Args:
            result: Mission result to log
        """
        log_file = os.path.join(self.output_folder, 'success.log')
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[SUCCESS] Mission {result.mission_id}\n")
            f.write(f"  URL: {result.site_url}\n")
            f.write(f"  Account: {result.account}\n")
            f.write(f"  ShortName: {result.short_name}\n")
            f.write(f"  Post URL: {result.post_url}\n")
            f.write(f"  Bank Type: {result.bank_type_used}\n")
            f.write(f"  Bank Name: {result.bank_name_used}\n")
            f.write(f"  Status: {result.http_status_post}\n")
            f.write(f"  Time: {result.execution_time:.2f}s\n")
            f.write("-" * 80 + "\n")
    
    def log_failure(self, result: MissionResult):
        """
        Log failed registration
        
        Args:
            result: Mission result to log
        """
        log_file = os.path.join(self.output_folder, 'failed.log')
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[FAILED] Mission {result.mission_id}\n")
            f.write(f"  URL: {result.site_url}\n")
            f.write(f"  Account: {result.account}\n")
            f.write(f"  Bank Type: {result.bank_type_used}\n")
            f.write(f"  Bank Name: {result.bank_name_used}\n")
            f.write(f"  Status: {result.http_status_post}\n")
            f.write(f"  Error: {result.error_message}\n")
            if result.response_body:
                f.write(f"  Response: {result.response_body[:200]}\n")
            f.write("-" * 80 + "\n")
    
    def save_results(self, results: List[MissionResult]):
        """
        Save all results to JSON file
        
        Args:
            results: List of mission results
        """
        result_file = os.path.join(self.output_folder, 'result.json')
        
        results_data = [result.to_dict() for result in results]
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)
    
    def save_statistics(self, state: MissionState, results: List[MissionResult]):
        """
        Save statistics to JSON file
        
        Args:
            state: Mission state with statistics
            results: List of mission results for additional stats
        """
        stats_file = os.path.join(self.output_folder, 'statistics.json')
        
        # Calculate additional statistics
        html_success = sum(
            1 for r in results
            if r.shortname_source == 'html_parsing' and r.status.value == 'success'
        )
        
        avg_response_time = sum(
            r.execution_time for r in results if r.execution_time > 0
        ) / len([r for r in results if r.execution_time > 0]) if results else 0
        
        # Per-bank statistics
        bank_stats = {}
        for r in results:
            bank_key = f"{r.bank_name_used} ({r.bank_type_used})"
            if bank_key not in bank_stats:
                bank_stats[bank_key] = {'success': 0, 'failed': 0}
            if r.status.value == 'success':
                bank_stats[bank_key]['success'] += 1
            else:
                bank_stats[bank_key]['failed'] += 1
        
        statistics = {
            **state.to_dict(),
            'html_parsing_success': html_success,
            'average_response_time': avg_response_time,
            'shortname_sources': {
                'html_parsing': sum(1 for r in results if r.shortname_source == 'html_parsing'),
                'other': sum(1 for r in results if r.shortname_source != 'html_parsing'),
                'unknown': sum(1 for r in results if r.shortname_source == 'unknown')
            },
            'bank_statistics': bank_stats
        }
        
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(statistics, f, indent=2, ensure_ascii=False)
