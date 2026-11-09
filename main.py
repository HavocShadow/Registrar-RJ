#!/usr/bin/env python3
"""
==========================================================
4 Mode:
  account-per-link : 1 link → banyak akun (default)
  link-per-account : 1 akun → banyak link
  one-to-one       : 1 link → 1 akun (berpasangan urutan, berhenti jika akun habis)
  repeat-accounts  : 1 link → 1 akun (akun diulang sampai semua link terdaftar)

Format file link (contoh: data/links/link.txt):
  https://url1.com/register
  https://url2.com/register
"""

import asyncio
import argparse
import sys
import time
import os
import json
import re
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from urllib.parse import urlparse

import aiohttp
from colorama import Fore, Style, init as colorama_init
from .proxy_settings import ProxySettings, load_proxy_settings

# Parser shortname (file terpisah)
from .parser import extract_shortname

colorama_init(autoreset=True)


# ==================== CONFIG ====================

USER_AGENT = (
    "Mozilla/5.0 (X11; CrOS x86_64 14541.0.0) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/150.0.0.0 Safari/537.36"
)

DEFAULT_TIMEOUT = 15
DEFAULT_CONCURRENCY = 10
MAX_RETRIES = 2


# ==================== MODELS ====================


@dataclass
class Site:
    url: str
    domain: str = ""

    def __post_init__(self):
        if not self.domain and self.url:
            parsed = urlparse(self.url)
            self.domain = f"{parsed.scheme}://{parsed.netloc}"

    def is_valid(self) -> bool:
        try:
            result = urlparse(self.url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False


@dataclass
class Account:
    username: str
    password: str
    fullname: str
    bank_type: str
    bank_name: str
    bank_number: str

    def is_valid(self) -> bool:
        return all(
            [
                self.username,
                self.password,
                self.fullname,
                self.bank_type,
                self.bank_name,
                self.bank_number,
            ]
        )

    def to_dict(self) -> Dict[str, str]:
        return {
            "username": self.username,
            "fullname": self.fullname,
            "bank_type": self.bank_type,
            "bank_name": self.bank_name,
            "bank_number": self.bank_number,
        }


@dataclass
class MissionResult:
    mission_id: int
    site_url: str
    username: str
    status: str = "pending"
    short_name: str = ""
    post_url: str = ""
    http_status_get: int = 0
    http_status_post: int = 0
    response_body: str = ""
    error_message: str = ""
    execution_time: float = 0.0

    @property
    def is_success(self) -> bool:
        return self.status == "success"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "site_url": self.site_url,
            "username": self.username,
            "status": self.status,
            "short_name": self.short_name,
            "http_status_get": self.http_status_get,
            "http_status_post": self.http_status_post,
            "response_body": self.response_body[:300] if self.response_body else "",
            "error_message": self.error_message,
            "execution_time": round(self.execution_time, 2),
        }


@dataclass
class MissionState:
    total_missions: int = 0
    completed_missions: int = 0
    success_count: int = 0
    failure_count: int = 0
    start_time: float = field(default_factory=time.time)

    @property
    def elapsed_time(self) -> float:
        return time.time() - self.start_time

    @property
    def success_rate(self) -> float:
        if self.completed_missions == 0:
            return 0.0
        return (self.success_count / self.completed_missions) * 100

    @property
    def checks_per_second(self) -> float:
        if self.elapsed_time == 0:
            return 0.0
        return self.completed_missions / self.elapsed_time


# ==================== DISPLAY ====================


def print_banner():
    print(f"""
{Fore.GREEN}
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║  ██████  ███████  ██████  ██  ██████  ███████ ██████  ███████  ║
║  ██   ██ ██      ██       ██ ██       ██      ██   ██ ██       ║
║  ██████  █████   ██   ███ ██ ██   ███ █████   ██████  ███████  ║
║  ██   ██ ██      ██    ██ ██ ██    ██ ██      ██   ██      ██  ║
║  ██   ██ ███████  ██████  ██  ██████  ███████ ██   ██ ███████  ║
║                                                                  ║
║         [ HTML PARSING REGISTRATION BOT v8.1 ]                  ║
║    [ 4 MODE: account-per-link | link-per-account ]              ║
║    [         one-to-one | repeat-accounts ]                     ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
{Style.RESET_ALL}
    """)


def print_section(title: str):
    print(f"\n{Fore.CYAN}{'=' * 64}")
    print(f"  {title}")
    print(f"{'=' * 64}{Style.RESET_ALL}")


def print_info(msg: str):
    print(f"{Fore.BLUE}🛠️  [INFO]{Style.RESET_ALL} {msg}")


def print_success(msg: str):
    print(f"{Fore.GREEN}✅ [SUCCESS]{Style.RESET_ALL} {msg}")


def print_warning(msg: str):
    print(f"{Fore.YELLOW}⚠️  [WARNING]{Style.RESET_ALL} {msg}")


def print_error(msg: str):
    print(f"{Fore.RED}💥 [ERROR]{Style.RESET_ALL} {msg}")


def print_progress(state: MissionState):
    percent = (
        (state.completed_missions / state.total_missions) * 100
        if state.total_missions > 0
        else 0
    )
    bar_length = 40
    filled = (
        int(bar_length * state.completed_missions // state.total_missions)
        if state.total_missions > 0
        else 0
    )
    bar = "█" * filled + "░" * (bar_length - filled)
    print(
        f"{Fore.CYAN}📊 [{bar}] {percent:.1f}% | "
        f"✅{state.success_count} ❌{state.failure_count} | "
        f"{state.checks_per_second:.1f}/s{Style.RESET_ALL}"
    )


def print_mission_result(
    mission_id: int,
    username: str,
    site: str,
    success: bool,
    short_name: str = "",
    reason: str = "",
):
    if success:
        print(
            f"{Fore.GREEN}✅ [{mission_id}] {username} @ {site} | SN: {short_name}{Style.RESET_ALL}"
        )
    else:
        tail = f" | {reason}" if reason else ""
        print(f"{Fore.RED}❌ [{mission_id}] {username} @ {site}{tail}{Style.RESET_ALL}")


# ==================== LOADER ====================


def load_sites(file_path: str) -> List[Site]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        raise FileNotFoundError(f"Links file not found: {file_path}")

    sites = []
    for line_num, line in enumerate(lines, 1):
        if line.startswith("#"):
            continue
        url = line.strip()
        if not url.startswith("http"):
            print_warning(f"Line {line_num}: Invalid URL, skipping: {url}")
            continue
        site = Site(url=url)
        if site.is_valid():
            sites.append(site)
        else:
            print_warning(f"Line {line_num}: Invalid URL format: {url}")

    if not sites:
        raise ValueError("No valid URLs found in file")
    return sites


def load_accounts(file_path: str) -> List[Account]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        raise FileNotFoundError(f"Accounts file not found: {file_path}")

    accounts = []
    for line_num, line in enumerate(lines, 1):
        if line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) != 6:
            print_warning(
                f"Line {line_num}: Expected 6 fields, got {len(parts)}, skipping"
            )
            continue
        account = Account(
            username=parts[0].strip(),
            password=parts[1].strip(),
            fullname=parts[2].strip(),
            bank_type=parts[3].strip(),
            bank_name=parts[4].strip(),
            bank_number=parts[5].strip(),
        )
        if account.is_valid():
            accounts.append(account)
        else:
            print_warning(f"Line {line_num}: Incomplete data, skipping")

    if not accounts:
        raise ValueError("No valid accounts found in file")
    return accounts


# ==================== MISSION PLAN GENERATORS ====================


def generate_plan_account_per_link(sites, accounts):
    return [(s, a) for s in sites for a in accounts]


def generate_plan_link_per_account(sites, accounts):
    return [(s, a) for a in accounts for s in sites]


def generate_plan_one_to_one(sites, accounts):
    n = min(len(sites), len(accounts))
    return [(sites[i], accounts[i]) for i in range(n)]


def generate_plan_repeat_accounts(sites, accounts):
    n = len(accounts)
    return [(s, accounts[i % n]) for i, s in enumerate(sites)]


# ==================== SUCCESS DETECTION ====================


def detect_success(status: int, body: str) -> bool:
    if status != 200 or not body:
        return False
    try:
        if body.strip().startswith("{"):
            resp_json = json.loads(body)
            code = resp_json.get("code")
            msg = str(resp_json.get("msg", "")).lower()
            if code == 9000 and "system error" in msg:
                return True
            if code == 422 and "username sudah ada" in msg:
                return True
            if code in [200, 2000, 0]:
                return True
            if code == 0 and "sukses" in msg:
                return True
    except Exception:
        pass
    positive = [
        "success",
        "berhasil",
        "sukses",
        "registrasi berhasil",
        "pendaftaran berhasil",
    ]
    lower = body.lower()
    if any(p in lower for p in positive):
        return True
    negative = ["error", "gagal", "not found", "unauthorized"]
    return not any(n in lower for n in negative)


# ==================== MISSION EXECUTOR ====================


class MissionExecutor:
    """Execute registration missions concurrently."""

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        concurrency: int = DEFAULT_CONCURRENCY,
        proxy_settings: Optional[ProxySettings] = None,
    ):
        self.timeout = timeout
        self.concurrency = concurrency
        self.proxy_settings = proxy_settings or ProxySettings(enabled=False)
        self.semaphore = asyncio.Semaphore(concurrency)
        self.state = MissionState()
        self.site_cache: Dict[str, str] = {}  # url → shortname
        self.url_cache: Dict[str, str] = {}  # url → final_url

    async def _get_shortname(
        self, session: aiohttp.ClientSession, url: str
    ) -> Tuple[Optional[str], Any]:
        """
        Return:
          (shortname, final_url)                → sukses
          (None, (http_status:int, reason:str)) → gagal
        """
        if url in self.site_cache:
            return self.site_cache[url], self.url_cache.get(url, url)

        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }

        for attempt in range(MAX_RETRIES + 1):
            try:
                async with session.get(
                    url,
                    headers=headers,
                    ssl=False,
                    allow_redirects=True,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    proxy=self.proxy_settings.url,
                    proxy_headers=self.proxy_settings.headers,
                ) as resp:
                    status = resp.status
                    final_url = str(resp.url) or url
                    raw = await resp.read()
                    html = raw.decode("utf-8", errors="replace")

                    if status != 200:
                        return None, (status, f"HTTP {status}")

                    low = html[:2000].lower()
                    if (
                        "just a moment" in low
                        or "cf-chl" in low
                        or "enable javascript and cookies" in low
                        or "attention required" in low
                    ):
                        return None, (status, "Cloudflare challenge")

                    if len(html) < 500:
                        return None, (status, f"Body too small ({len(html)}b)")

                    sn = extract_shortname(html)
                    if not sn:
                        # simpan untuk inspeksi
                        try:
                            debug_dir = Path(__file__).resolve().parents[1] / "debug"
                            debug_dir.mkdir(exist_ok=True)
                            safe = re.sub(r"[^A-Za-z0-9]+", "_", url)[:80]
                            (debug_dir / f"{safe}.html").write_text(
                                html, encoding="utf-8"
                            )
                        except Exception:
                            pass
                        return None, (status, f"ShortName not found ({len(html)}b)")

                    self.site_cache[url] = sn
                    self.url_cache[url] = final_url
                    return sn, final_url

            except asyncio.TimeoutError:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1.0 * (attempt + 1))
                    continue
                return None, (0, "Timeout")

            except aiohttp.ClientError as e:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1.0 * (attempt + 1))
                    continue
                return None, (0, f"{type(e).__name__}: {e}")

            except Exception as e:
                return None, (0, f"{type(e).__name__}: {e}")

        return None, (0, "Unknown error")

    async def _register_user(
        self, session, base_url: str, short_name: str, account: Account
    ) -> Tuple[int, str]:
        post_url = f"{base_url}/api/AppService/AddUserInfo"
        payload = {
            "Account": account.username,
            "Password": account.password,
            "Email": "",
            "BankType": account.bank_type,
            "BankNum": account.bank_number,
            "BankName": account.bank_name,
            "FullName": account.fullname,
            "userMoneyPwd1": account.password,
            "userMoneyPwd2": account.password,
            "ShortName": short_name,
        }
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "language": "id",
            "origin": base_url,
            "referer": f"{base_url}/",
        }
        async with session.post(
            post_url,
            headers=headers,
            json=payload,
            ssl=False,
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            proxy=self.proxy_settings.url,
            proxy_headers=self.proxy_settings.headers,
        ) as resp:
            body = await resp.text()
            return resp.status, body

    async def execute_mission(
        self, session, site: Site, account: Account, mission_id: int
    ) -> MissionResult:
        start_time = time.time()
        result = MissionResult(
            mission_id=mission_id,
            site_url=site.url,
            username=account.username,
        )

        try:
            short_name, meta = await self._get_shortname(session, site.url)

            if not short_name:
                if isinstance(meta, tuple):
                    http_status, reason = meta
                else:
                    http_status, reason = 0, "ShortName not found"
                result.status = "failed"
                result.http_status_get = http_status
                result.error_message = reason
                self.state.failure_count += 1
                self.state.completed_missions += 1
                print_mission_result(
                    mission_id, account.username, site.domain, False, reason=reason
                )
                return result

            result.short_name = short_name
            final_url = meta  # di sini meta = final_url string

            parsed = urlparse(final_url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            result.post_url = f"{base_url}/api/AppService/AddUserInfo"

            status, body = await self._register_user(
                session, base_url, short_name, account
            )
            result.http_status_post = status
            result.response_body = body

            if detect_success(status, body):
                result.status = "success"
                self.state.success_count += 1
                print_mission_result(
                    mission_id, account.username, site.domain, True, short_name
                )
            else:
                result.status = "failed"
                result.error_message = f"HTTP {status}"
                self.state.failure_count += 1
                print_mission_result(
                    mission_id,
                    account.username,
                    site.domain,
                    False,
                    reason=f"HTTP {status}",
                )

        except asyncio.TimeoutError:
            result.status = "failed"
            result.error_message = "Timeout"
            self.state.failure_count += 1
            print_mission_result(
                mission_id, account.username, site.domain, False, reason="Timeout"
            )

        except Exception as e:
            result.status = "failed"
            result.error_message = str(e)[:150]
            self.state.failure_count += 1
            print_mission_result(
                mission_id, account.username, site.domain, False, reason=str(e)[:60]
            )

        result.execution_time = time.time() - start_time
        self.state.completed_missions += 1
        return result

    async def execute_all(
        self, mission_plan: List[Tuple[Site, Account]]
    ) -> List[MissionResult]:
        self.state.total_missions = len(mission_plan)

        print_section("STARTING REGISTRATION")
        print_info(f"Total Missions : {len(mission_plan)}")
        print_info(f"Concurrency    : {self.concurrency}")
        print_info(f"Timeout        : {self.timeout}s")
        print()

        connector = aiohttp.TCPConnector(
            limit=self.concurrency * 2,
            limit_per_host=10,
            ssl=False,
        )

        async with aiohttp.ClientSession(connector=connector) as session:

            async def run_one(idx, site, account):
                async with self.semaphore:
                    if (idx + 1) % 10 == 0 or (idx + 1) == self.state.total_missions:
                        print_progress(self.state)
                    return await self.execute_mission(session, site, account, idx + 1)

            tasks = [
                run_one(i, site, account)
                for i, (site, account) in enumerate(mission_plan)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        valid: List[MissionResult] = []
        for r in results:
            if isinstance(r, MissionResult):
                valid.append(r)
            elif isinstance(r, Exception):
                self.state.failure_count += 1
                print_error(f"Mission exception: {r}")
        return valid


# ==================== SAVE RESULTS ====================


def save_results(
    results: List[MissionResult],
    state: MissionState,
    output_folder: str = "output_regis",
):
    os.makedirs(output_folder, exist_ok=True)

    with open(
        os.path.join(output_folder, "regis_results.json"), "w", encoding="utf-8"
    ) as f:
        json.dump([r.to_dict() for r in results], f, indent=2, ensure_ascii=False)

    success_list = [r for r in results if r.is_success]
    if success_list:
        with open(
            os.path.join(output_folder, "success.txt"), "w", encoding="utf-8"
        ) as f:
            f.write("SUCCESSFUL REGISTRATIONS\n" + "=" * 60 + "\n\n")
            f.write(f"Total: {len(success_list)}\n\n")
            for r in success_list:
                f.write(f"Username  : {r.username}\n")
                f.write(f"Site      : {r.site_url}\n")
                f.write(f"ShortName : {r.short_name}\n")
                f.write(f"Time      : {r.execution_time:.2f}s\n")
                f.write("-" * 60 + "\n")

    failed_list = [r for r in results if not r.is_success]
    if failed_list:
        with open(
            os.path.join(output_folder, "failed.txt"), "w", encoding="utf-8"
        ) as f:
            f.write("FAILED REGISTRATIONS\n" + "=" * 60 + "\n\n")
            f.write(f"Total: {len(failed_list)}\n\n")
            for r in failed_list:
                f.write(f"Username : {r.username}\n")
                f.write(f"Site     : {r.site_url}\n")
                f.write(f"Error    : {r.error_message}\n")
                f.write("-" * 60 + "\n")

    print_section("REGISTRATION SUMMARY")
    print_info(f"Total Missions  : {state.total_missions}")
    print_success(f"Success         : {state.success_count}")
    print_error(f"Failed          : {state.failure_count}")
    print_info(f"Success Rate    : {state.success_rate:.1f}%")
    print_info(f"Elapsed Time    : {state.elapsed_time:.1f}s")
    print_info(f"Speed           : {state.checks_per_second:.1f} missions/s")

    site_stats: Dict[str, Dict[str, int]] = {}
    for r in results:
        domain = urlparse(r.site_url).netloc
        site_stats.setdefault(domain, {"success": 0, "failed": 0})
        if r.is_success:
            site_stats[domain]["success"] += 1
        else:
            site_stats[domain]["failed"] += 1

    if len(site_stats) <= 20:
        print_section("PER-SITE SUMMARY")
        for domain, stats in sorted(site_stats.items()):
            total = stats["success"] + stats["failed"]
            rate = (stats["success"] / total * 100) if total > 0 else 0
            print_info(f"  {domain}: {stats['success']}/{total} ({rate:.1f}%)")

    print_success(f"\n📁 Results saved to: {output_folder}/")
    print_info("  - regis_results.json (full data)")
    print_info("  - success.txt (successful)")
    print_info("  - failed.txt (failed)")


# ==================== MAIN ====================


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="RegisV8.1 - HTML Parsing Registration Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --dashboard
  python main.py --links data/links/link.txt --accounts data/accounts/accounts.txt
  python main.py --links data/links/link.txt --accounts data/accounts/accounts.txt --mode one-to-one
  python main.py --links data/links/link.txt --accounts data/accounts/accounts.txt --mode repeat-accounts --concurrency 20
        """,
    )
    parser.add_argument("--links", help="File containing target URLs (1 per line)")
    parser.add_argument(
        "--accounts",
        help="File containing accounts (user|pass|name|banktype|bankname|banknum)",
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Open the read-only Textual dashboard for previously saved results.",
    )
    parser.add_argument(
        "--results",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "output_regis" / "regis_results.json",
        help="JSON results file used with --dashboard.",
    )
    parser.add_argument(
        "--mode",
        choices=[
            "account-per-link",
            "link-per-account",
            "one-to-one",
            "repeat-accounts",
        ],
        default="account-per-link",
        help="Execution mode (default: account-per-link)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help=f"Max concurrent missions (default: {DEFAULT_CONCURRENCY})",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Request timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--output", default="output_regis", help="Output folder (default: output_regis)"
    )

    args = parser.parse_args()
    if not args.dashboard and (not args.links or not args.accounts):
        parser.error("--links and --accounts are required unless --dashboard is used.")
    return args


async def main():
    try:
        args = parse_arguments()

        if args.dashboard:
            from .results_dashboard import ResultsDashboard

            await ResultsDashboard(args.results.expanduser()).run_async()
            return

        print_banner()

        try:
            proxy_settings = load_proxy_settings()
        except ValueError as exc:
            print_error(f"Invalid proxy configuration: {exc}")
            return

        if proxy_settings.enabled:
            print_info(f"HTTP proxy enabled: {proxy_settings.endpoint}")
        else:
            print_info("HTTP proxy disabled (PROXY_ENABLED=false)")

        # ---- Load files ----
        print_section("LOADING LINKS")
        try:
            sites = load_sites(args.links)
            print_success(f"Loaded {len(sites)} links")
        except Exception as e:
            print_error(f"Error loading links: {e}")
            return

        print_section("LOADING ACCOUNTS")
        try:
            accounts = load_accounts(args.accounts)
            print_success(f"Loaded {len(accounts)} accounts")
        except Exception as e:
            print_error(f"Error loading accounts: {e}")
            return

        # ---- Generate plan ----
        print_section("GENERATING MISSION PLAN")
        mode_desc = {
            "account-per-link": f"1 link → semua akun ({len(sites)}×{len(accounts)})",
            "link-per-account": f"1 akun → semua link ({len(accounts)}×{len(sites)})",
            "one-to-one": f"1 link → 1 akun (max {min(len(sites), len(accounts))})",
            "repeat-accounts": f"1 link → 1 akun, akun diulang ({len(sites)} links, {len(accounts)} akun)",
        }
        print_info(f"Mode: {args.mode}")
        print_info(mode_desc[args.mode])

        if args.mode == "account-per-link":
            plan = generate_plan_account_per_link(sites, accounts)
        elif args.mode == "link-per-account":
            plan = generate_plan_link_per_account(sites, accounts)
        elif args.mode == "one-to-one":
            plan = generate_plan_one_to_one(sites, accounts)
            if len(sites) != len(accounts):
                print_warning(
                    f"Links ({len(sites)}) ≠ Accounts ({len(accounts)}). "
                    f"Only {len(plan)} missions will run."
                )
        else:
            plan = generate_plan_repeat_accounts(sites, accounts)

        if not plan:
            print_error("No missions generated! Check your input files.")
            return
        print_info(f"Total missions: {len(plan)}")

        # ---- Execute ----
        executor = MissionExecutor(
            timeout=args.timeout,
            concurrency=args.concurrency,
            proxy_settings=proxy_settings,
        )
        results = await executor.execute_all(plan)

        # ---- Save ----
        print_section("SAVING RESULTS")
        save_results(results, executor.state, args.output)

        if executor.state.success_count > 0:
            print_success(
                f"\n🎉 {executor.state.success_count} registrations successful!"
            )
        else:
            print_warning("\n😔 No successful registrations")

    except KeyboardInterrupt:
        print_warning("\n\nProcess interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDashboard/application interrupted by user.")
