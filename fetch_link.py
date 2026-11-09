#!/usr/bin/env python3
"""
Domain Redirect Tracker
=======================
Ambil data dari yukcari.net/domains.json, follow redirect, dan simpan link terbaru
"""

import json
import requests
import time
import re
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse, urljoin
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============================================================
# KONFIGURASI
# ============================================================

YUKCARI_URL = "https://yukcari.net/domains.json"
DOMAIN_DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "domains"
OUTPUT_FILE = DOMAIN_DATA_DIR / "link_terbaru_yukcari.txt"
OUTPUT_JSON = DOMAIN_DATA_DIR / "link_terbaru_yukcari.json"
TIMEOUT = 30
MAX_REDIRECTS = 10
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# ============================================================
# LIST URL YANG DICARI
# ============================================================

TARGET_URLS = [
    "https://studiobet78x.ink",
    "https://cs005.dw77a.store",
    "https://fla001.flora77x.store",
    "https://fu005.fauna189.store",
    "https://fun002.jarot88b.site",
    "https://game001.bunda128.org",
    "https://cc003.bigwin189c.live",
    "https://game001.doyok365.online",
    "https://game001.emas128.online",
    "https://game001.gembul189a.live",
    "https://ma002.dana189b.online",
    "https://game001.horas79.store",
    "https://ms001.gacorx189a.online",
    "https://ss001.suhu189x.site",
    "https://mp002.gunung128.live",
    "https://game001.lele189c.live",
    "https://game001.lentera189.live",
    "https://game001.terbang128.org",
    "https://game001.virgo95a.site",
    "https://game001.yoman189.store",
    "https://game002.dahlia19.online",
    "https://cc003.brodi77b.online",
    "https://mk004.mulia189a.site",
    "https://goel005.gul911.store",
    "https://pus001.pusaka189x.store",
    "https://qr002.qris189.store",
    "https://rain002.orin23a.online",
    "https://bad001.paradewa89w.online",
    "https://res001.restu189vip.store",
    "https://rg001.braga89x.store",
    "https://rit001.ritual79a.store",
    "https://rm005.armorbet78a.site",
    "https://rr001.tarung189x.site",
    "https://rt002.kramat77a.live",
    "https://rt002.krtonbet.live",
    "https://sa002.gg189a.site",
    "https://sa108.senja128.live",
    "https://sak002.sakti79a.site",
    "https://sam002.sambora77.site",
    "https://sat005.satebetx.vip",
    "https://scor002.scorpio95.site",
    "https://sk003.alaska79b.site",
    "https://soon003.arwana189b.xyz",
    "https://spa002.spartan95x.online",
    "https://ss001.bigcor78c.site",
    "https://aa001.anakdina88c.site",
    "https://aa001.asgar10.shop",
    "https://aa003.kuda189a.site",
    "https://aa003.pararaja77c.online",
    "https://ac001.merak78x.online",
    "https://ada001.madara77b.online",
    "https://ads001.adsportsvip.site",
    "https://am005.ovrbola.site",
    "https://man001.hanoman77-x.store",
    "https://game004.zoro10.live",
    "https://ama001.amel189.store",
    "https://an003.titan79c.store",
    "https://ang003.angker77c.site",
    "https://apt002.apg9b.site",
    "https://arie001.aries95.site",
    "https://aru002.arjuna189a.live",
    "https://as002.asiacasino89x.online",
    "https://ats001.atlas189.online",
    "https://bd001.azura77c.live",
    "https://ba001.bigbet78.online",
    "https://ba003.nabila77x.store",
    "https://ba005.bahtera78.store",
    "https://ma002.acak77b.store",
    "https://bac001.cuan805x.online",
    "https://bac002.nemo189b.online",
    "https://bac001.studiobet78a.live",
    "https://su001.puri189c.site",
    "https://back001.bnga189.site",
    "https://back001.criptobet77a.online",
    "https://back001.hantam88x.site",
    "https://back001.kaisar189x.online",
    "https://back001.uranus189c.live",
    "https://bad002.sabana88.site",
    "https://ban002.jalang189c.site",
    "https://bar001.barabet78x.site",
    "https://bas003.baskara89a.live",
    "https://bb004.bambu189.online",
    "https://bec001.bcl138a.online",
    "https://bey001.byon189.site",
    "https://bi002.arimbi189x.site",
    "https://bd001.preman189c.live",
    "https://boom001.taxibet88b.online",
    "https://boy001.koboy911a.site",
    "https://cs001.laura77a.store",
    "https://bus003.tembus78x.online",
    "https://game017.astro128.info",
    "https://cc001.fanatik99.online",
    "https://cc001.gen189.online",
    "https://cc001.letnan189a.online",
    "https://cc003.ratu555a.store",
    "https://cc001.sahara88a.online",
    "https://cc001.sanjaya78.online",
    "https://cc002.sekawan78b.live",
    "https://cc002.sinar79b.online",
    "https://cc001.tupay79a.site",
    "https://cc001.wwb9b.shop",
    "https://cc002.aronbet88c.online",
    "https://cc002.bae69.site",
    "https://cc002.bigbos79b.site",
    "https://cc002.demon189a.store",
    "https://cc002.karma79x.online",
    "https://cc002.matador78b.site",
    "https://cc002.navibetb.site",
]

# ============================================================
# FUNGSI
# ============================================================

def get_domain_from_url(url: str) -> str:
    """Ekstrak domain dari URL"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        # Hapus www.
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except:
        return url

def follow_redirect(url: str, max_redirects: int = MAX_REDIRECTS) -> Dict:
    """
    Follow redirect hingga titik akhir
    """
    result = {
        "original": url,
        "final_url": url,
        "status": "unknown",
        "redirects": [],
        "error": None,
        "domain": get_domain_from_url(url),
        "is_redirect": False,
    }
    
    current_url = url
    redirect_count = 0
    
    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })
        
        # Gunakan head request dulu (lebih cepat)
        try:
            resp = session.head(current_url, timeout=TIMEOUT, verify=False, allow_redirects=False)
        except:
            # Fallback ke get
            resp = session.get(current_url, timeout=TIMEOUT, verify=False, allow_redirects=False)
        
        # Cek redirect
        while resp.status_code in [301, 302, 303, 307, 308] and redirect_count < max_redirects:
            redirect_count += 1
            location = resp.headers.get("Location", "")
            
            if not location:
                break
            
            # Handle relative URL
            if location.startswith("/"):
                parsed = urlparse(current_url)
                location = f"{parsed.scheme}://{parsed.netloc}{location}"
            elif not location.startswith(("http://", "https://")):
                # Mungkin URL relatif
                parsed = urlparse(current_url)
                base = f"{parsed.scheme}://{parsed.netloc}"
                location = urljoin(base, location)
            
            result["redirects"].append({
                "from": current_url,
                "to": location,
                "status": resp.status_code,
            })
            
            current_url = location
            result["domain"] = get_domain_from_url(current_url)
            
            try:
                resp = session.head(current_url, timeout=TIMEOUT, verify=False, allow_redirects=False)
            except:
                resp = session.get(current_url, timeout=TIMEOUT, verify=False, allow_redirects=False)
        
        # Dapatkan final URL
        final_response = session.get(current_url, timeout=TIMEOUT, verify=False, allow_redirects=True)
        result["final_url"] = final_response.url
        result["status"] = "success"
        result["status_code"] = final_response.status_code
        
        # Cek apakah ada redirect (perubahan domain)
        if result["final_url"] != url:
            result["is_redirect"] = True
            result["domain"] = get_domain_from_url(result["final_url"])
        else:
            result["is_redirect"] = False
        
    except requests.exceptions.Timeout:
        result["status"] = "timeout"
        result["error"] = "Connection timeout"
    except requests.exceptions.ConnectionError:
        result["status"] = "connection_error"
        result["error"] = "Connection failed"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    
    return result

def fetch_yukcari_data() -> Dict:
    """Ambil data dari yukcari.net/domains.json"""
    try:
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        }
        resp = requests.get(YUKCARI_URL, headers=headers, timeout=TIMEOUT, verify=False)
        
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"[ERROR] Gagal fetch yukcari: {resp.status_code}")
            return {}
    except Exception as e:
        print(f"[ERROR] Gagal fetch yukcari: {e}")
        return {}

def find_url_in_yukcari(yukcari_data: Dict, target_url: str) -> Optional[str]:
    """
    Cari URL di data yukcari.net
    """
    # Ekstrak domain dari target
    target_domain = get_domain_from_url(target_url)
    
    # Cari di brands
    brands = yukcari_data.get("brands", [])
    
    for brand in brands:
        # Cek URL
        brand_url = brand.get("url", "")
        if target_url in brand_url or brand_url in target_url:
            return brand_url
        
        # Cek candidates
        candidates = brand.get("candidates", [])
        for candidate in candidates:
            if target_url in candidate or candidate in target_url:
                return brand_url
        
        # Cek domains
        domains = brand.get("domains", [])
        for domain in domains:
            if target_domain in domain or domain in target_domain:
                # Ambil URL pertama yang tersedia
                if candidates:
                    return candidates[0]
                if brand_url:
                    return brand_url
        
        # Cek aliases
        aliases = brand.get("aliases", [])
        for alias in aliases:
            if alias in target_domain:
                if brand.get("url"):
                    return brand.get("url")
    
    # Jika tidak ditemukan di yukcari, return target_url asli
    return target_url

def normalize_url(url: str) -> str:
    """Normalisasi URL"""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    # Hapus trailing slash
    url = url.rstrip("/")
    return url

# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("DOMAIN REDIRECT TRACKER")
    print("=" * 60)
    print()
    
    # 1. Fetch data dari yukcari.net
    print("[1] Mengambil data dari yukcari.net...")
    yukcari_data = fetch_yukcari_data()
    
    if not yukcari_data:
        print("[WARNING] Gagal fetch yukcari.net, akan menggunakan URL asli")
    
    print(f"    Total brands: {len(yukcari_data.get('brands', []))}")
    print()
    
    # 2. Proses setiap URL
    print("[2] Memproses redirect...")
    print("-" * 60)
    
    results = []
    found_urls = []
    not_found_urls = []
    error_urls = []
    
    for idx, target_url in enumerate(TARGET_URLS, 1):
        target_url = normalize_url(target_url)
        print(f"[{idx:3d}] {target_url}")
        
        # Cari di yukcari
        if yukcari_data:
            found_url = find_url_in_yukcari(yukcari_data, target_url)
            if found_url and found_url != target_url:
                print(f"    → Ditemukan di yukcari: {found_url}")
                target_url = normalize_url(found_url)
                found_urls.append(target_url)
            else:
                print(f"    → Tidak ditemukan di yukcari, pakai asli")
                not_found_urls.append(target_url)
        else:
            not_found_urls.append(target_url)
        
        # Follow redirect
        result = follow_redirect(target_url)
        results.append(result)
        
        # Print hasil
        if result["status"] == "success":
            if result["is_redirect"]:
                print(f"    → REDIRECT: {result['final_url']}")
                if result["redirects"]:
                    for r in result["redirects"]:
                        print(f"        {r['status']}: {r['from']} → {r['to']}")
            else:
                print(f"    → OK: {result['final_url']}")
        else:
            print(f"    → ERROR: {result['error']}")
            error_urls.append(target_url)
        
        # Tambahkan delay untuk menghindari rate limit
        if idx < len(TARGET_URLS):
            time.sleep(0.5)
        
        print()
    
    # 3. Simpan hasil
    print("[3] Menyimpan hasil...")
    print("-" * 60)
    DOMAIN_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Buat mapping URL lama → URL baru
    url_mapping = {}
    for result in results:
        if result["status"] == "success":
            url_mapping[result["original"]] = result["final_url"]
    
    # Simpan ke file text
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("# ============================================================\n")
        f.write("# LINK TERBARU - Yukcari.net Redirect Tracker\n")
        f.write(f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Total: {len(results)}\n")
        f.write("# ============================================================\n\n")
        
        f.write("[URLS]\n")
        for result in results:
            if result["status"] == "success":
                f.write(f"{result['final_url']}\n")
        
        f.write("\n\n[MAPPING]\n")
        for original, final in url_mapping.items():
            f.write(f"{original} → {final}\n")
        
        f.write("\n\n[STATISTICS]\n")
        f.write(f"Total: {len(results)}\n")
        f.write(f"Success: {sum(1 for r in results if r['status'] == 'success')}\n")
        f.write(f"Redirect: {sum(1 for r in results if r['is_redirect'])}\n")
        f.write(f"Error: {len(error_urls)}\n")
        f.write(f"Found in yukcari: {len(found_urls)}\n")
        f.write(f"Not found in yukcari: {len(not_found_urls)}\n")
    
    # Simpan ke JSON
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total": len(results),
            "urls": [r["final_url"] for r in results if r["status"] == "success"],
            "mapping": url_mapping,
            "details": results,
            "statistics": {
                "success": sum(1 for r in results if r["status"] == "success"),
                "redirect": sum(1 for r in results if r["is_redirect"]),
                "error": len(error_urls),
                "found_in_yukcari": len(found_urls),
                "not_found_in_yukcari": len(not_found_urls),
            }
        }, f, indent=2)
    
    print(f"✅ File disimpan:")
    print(f"   - {OUTPUT_FILE}")
    print(f"   - {OUTPUT_JSON}")
    print()
    
    # 4. Statistik
    print("[4] STATISTIK")
    print("-" * 60)
    print(f"Total URL: {len(results)}")
    print(f"  ✅ Success: {sum(1 for r in results if r['status'] == 'success')}")
    print(f"  🔀 Redirect: {sum(1 for r in results if r['is_redirect'])}")
    print(f"  ❌ Error: {len(error_urls)}")
    print(f"  📦 Found in yukcari: {len(found_urls)}")
    print(f"  📦 Not found in yukcari: {len(not_found_urls)}")
    print()
    
    # 5. Tampilkan contoh hasil
    print("[5] Contoh Hasil:")
    print("-" * 60)
    for i, result in enumerate(results[:5], 1):
        if result["status"] == "success":
            print(f"{i}. {result['original']}")
            if result["is_redirect"]:
                print(f"   → {result['final_url']}")
            else:
                print(f"   → (no redirect)")
        else:
            print(f"{i}. {result['original']} → ERROR: {result['error']}")
    
    if len(results) > 5:
        print(f"... dan {len(results)-5} lainnya")
    
    print()
    print("=" * 60)
    print("SELESAI!")

if __name__ == "__main__":
    main()
