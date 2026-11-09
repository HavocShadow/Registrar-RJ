# test_aiohttp.py
import asyncio
import aiohttp
from pathlib import Path

URL = "https://abilawa99b.online/"
UA = ("Mozilla/5.0 (X11; CrOS x86_64 14541.0.0) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36")

async def main():
    headers = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
    }
    async with aiohttp.ClientSession() as s:
        try:
            async with s.get(URL, headers=headers, ssl=False,
                             allow_redirects=True,
                             timeout=aiohttp.ClientTimeout(total=15)) as r:
                body = await r.read()
                text = body.decode("utf-8", "replace")
                print("STATUS        :", r.status)
                print("FINAL URL     :", r.url)
                print("LEN           :", len(body))
                print("CONTENT-TYPE  :", r.headers.get("content-type"))
                print("SERVER        :", r.headers.get("server"))
                print("CF-RAY        :", r.headers.get("cf-ray"))
                print("HAS appSetting:", "appSetting" in text)
                print("HAS systemShortName:", "systemShortName" in text)
                print("HEAD 300      :", repr(text[:300]))
                Path("/tmp/aio_resp.html").write_text(text, encoding="utf-8")
        except Exception as e:
            print("EXCEPTION:", type(e).__name__, ":", e)

asyncio.run(main())
