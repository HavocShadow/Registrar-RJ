#!/usr/bin/env python3
"""
Display module for RegisV8
Handles all console output with colored formatting
"""

import json
from typing import Dict, Any
from colorama import Fore, Style, init as colorama_init

# Initialize colorama
colorama_init(autoreset=True)


def print_banner():
    """Display application banner"""
    banner = f"""
{Fore.GREEN}
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║  ██████  ███████ ██████  ██  ██████  ███████ ██████  ███████  ║
║  ██   ██ ██      ██   ██ ██ ██       ██      ██   ██ ██       ║
║  ██████  █████   ██████  ██ ██   ███ █████   ██████  ███████  ║
║  ██   ██ ██      ██   ██ ██ ██    ██ ██      ██   ██      ██  ║
║  ██   ██ ███████ ██   ██ ██  ██████  ███████ ██   ██ ███████  ║
║                                                                ║
║              [ HTML PARSING REGISTRATION BOT v8.0 ]           ║
║                   [ MODULAR ARCHITECTURE ]                    ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
{Style.RESET_ALL}
    """
    print(banner)


def print_section(title: str):
    """Display section header"""
    print(f"\n{Fore.CYAN}╔════════════════════════════════════════════════════════════════╗")
    print(f"║ {title:^58} ║")
    print(f"╚════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}")


def print_info(msg: str):
    """Display info message"""
    print(f"{Fore.BLUE}🛠️  [INFO]{Style.RESET_ALL} {msg}")


def print_success(msg: str):
    """Display success message"""
    print(f"{Fore.GREEN}✅ [SUCCESS]{Style.RESET_ALL} {msg}")


def print_warning(msg: str):
    """Display warning message"""
    print(f"{Fore.YELLOW}⚠️  [WARNING]{Style.RESET_ALL} {msg}")


def print_error(msg: str):
    """Display error message"""
    print(f"{Fore.RED}💥 [ERROR]{Style.RESET_ALL} {msg}")


def print_target(url: str, mission_id: int):
    """Display target URL"""
    print(f"{Fore.RED}🎯 [TARGET-M{mission_id}]{Style.RESET_ALL} {url}")


def print_payload(data: Dict[str, Any], mission_id: int):
    """Display request payload"""
    print(f"{Fore.YELLOW}📦 [PAYLOAD-M{mission_id}]{Style.RESET_ALL}")
    for key, value in data.items():
        if key == "Password" or key == "userMoneyPwd1" or key == "userMoneyPwd2":
            print(f"    {Fore.WHITE}{key}: {Fore.CYAN}***{Style.RESET_ALL}")
        else:
            print(f"    {Fore.WHITE}{key}: {Fore.CYAN}{value}{Style.RESET_ALL}")


def print_response(status: int, body: str, mission_id: int):
    """Display response details"""
    color = Fore.GREEN if status == 200 else Fore.RED
    print(f"{color}📡 [RESPONSE-M{mission_id}]{Style.RESET_ALL} HTTP {status}")
    
    if body:
        try:
            resp_json = json.loads(body)
            print(f"    {Fore.WHITE}{json.dumps(resp_json, indent=2)}{Style.RESET_ALL}")
        except:
            snippet = body[:200] + "..." if len(body) > 200 else body
            print(f"    {Fore.WHITE}{snippet}{Style.RESET_ALL}")


def print_progress(current: int, total: int, message: str = ""):
    """Display progress bar"""
    percent = (current / total) * 100 if total > 0 else 0
    bar_length = 50
    filled_length = int(bar_length * current // total) if total > 0 else 0
    bar = '█' * filled_length + '░' * (bar_length - filled_length)
    
    print(f"{Fore.CYAN}📊 [PROGRESS]{Style.RESET_ALL} [{bar}] {percent:.1f}% - {message}")


def print_concurrent_status(active: int, total: int, concurrency: int):
    """Display concurrent execution status"""
    print(f"{Fore.MAGENTA}🚀 [CONCURRENT]{Style.RESET_ALL} "
          f"Active: {active}/{total} (Max: {concurrency} threads)")


def print_stats(success_count: int, total_count: int, elapsed_time: float):
    """Display statistics"""
    success_rate = (success_count / total_count) * 100 if total_count > 0 else 0
    avg_time = elapsed_time / total_count if total_count > 0 else 0
    
    print(f"{Fore.MAGENTA}📈 [STATS]{Style.RESET_ALL} "
          f"Success: {success_count}/{total_count} ({success_rate:.1f}%)")
    print(f"{Fore.MAGENTA}     ⏱️  Elapsed: {elapsed_time:.1f}s | "
          f"Avg: {avg_time:.2f}s/call{Style.RESET_ALL}")


def print_mission_result(mission_id: int, success: bool, shortname: str = None):
    """Display individual mission result"""
    if success:
        print_success(f"Mission {mission_id}: 🎉 REGISTRATION SUCCESSFUL!")
        if shortname:
            print_info(f"  ShortName: {shortname}")
    else:
        print_error(f"Mission {mission_id}: Registration failed")


def print_summary(state):
    """Display final summary"""
    print_section("DEPLOYMENT COMPLETE")
    print_info(f"Total Execution Time: {state.elapsed_time:.2f} seconds")
    print_info(f"Total Missions: {state.total_missions}")
    print_success(f"Successful: {state.success_count}")
    print_error(f"Failed: {state.failure_count}")
    
    if state.success_count > 0:
        print_success(f"Success Rate: {state.success_rate:.1f}%")
        print_success(f"Average Time per Mission: {state.avg_time_per_mission:.3f}s")
        print_success(f"Throughput: {state.throughput:.1f} requests/second")
