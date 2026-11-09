#!/usr/bin/env python3
"""
HTTP Client module for RegisV8
Handles all HTTP communications (GET/POST) with retry mechanism
"""

import asyncio
import aiohttp
from typing import Dict, Optional, Tuple, Any
from urllib.parse import urlparse


class HTTPClient:
    """Async HTTP client with session management and retry support"""
    
    def __init__(
        self,
        user_agent: str,
        timeout: int = 15,
        max_redirects: int = 5,
        ssl_verify: bool = False,
        max_retries: int = 3
    ):
        """
        Initialize HTTP client
        
        Args:
            user_agent: User-Agent string
            timeout: Request timeout in seconds
            max_redirects: Maximum number of redirects to follow
            ssl_verify: Verify SSL certificates
            max_retries: Maximum number of retry attempts
        """
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_redirects = max_redirects
        self.ssl_verify = ssl_verify
        self.max_retries = max_retries
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Create session when entering context"""
        connector = aiohttp.TCPConnector(
            ssl=self.ssl_verify,
            limit=100,
            limit_per_host=30
        )
        timeout_obj = aiohttp.ClientTimeout(total=self.timeout)
        
        self.session = aiohttp.ClientSession(
            timeout=timeout_obj,
            connector=connector
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close session when exiting context"""
        if self.session:
            await self.session.close()
    
    def _build_headers(self, base_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Build request headers"""
        headers = {
            "User-Agent": self.user_agent,
            "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
            "Connection": "keep-alive",
        }
        
        if base_headers:
            headers.update(base_headers)
        
        return headers
    
    async def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        follow_redirects: bool = True
    ) -> Tuple[int, str, Dict[str, str], str]:
        """
        Perform GET request with redirect handling
        
        Args:
            url: Target URL
            headers: Additional headers
            follow_redirects: Whether to follow redirects
            
        Returns:
            Tuple of (status_code, body, headers, final_url)
        """
        request_headers = self._build_headers(headers)
        retries = 0
        
        while retries <= self.max_retries:
            try:
                if not self.session:
                    raise RuntimeError("HTTPClient session not initialized")
                
                result = await self._execute_get(
                    url, request_headers, follow_redirects
                )
                
                return result
                
            except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                retries += 1
                if retries > self.max_retries:
                    return (408 if isinstance(e, asyncio.TimeoutError) else 500,
                            str(e), {}, url)
                
                # Wait before retry (exponential backoff)
                await asyncio.sleep(0.5 * retries)
        
        return (500, "Max retries exceeded", {}, url)
    
    async def _execute_get(
        self,
        url: str,
        headers: Dict[str, str],
        follow_redirects: bool
    ) -> Tuple[int, str, Dict[str, str], str]:
        """Execute GET request with optional redirect following"""
        redirect_count = 0
        current_url = url
        
        while redirect_count < (self.max_redirects if follow_redirects else 1):
            async with self.session.get(
                current_url,
                headers=headers,
                allow_redirects=False
            ) as resp:
                body = await resp.text()
                resp_headers = dict(resp.headers)
                
                # Handle redirects
                if follow_redirects and resp.status in (301, 302, 303, 307, 308):
                    location = resp.headers.get('Location')
                    if location:
                        redirect_count += 1
                        
                        # Handle relative redirects
                        if location.startswith('/'):
                            parsed = urlparse(current_url)
                            location = f"{parsed.scheme}://{parsed.netloc}{location}"
                        
                        current_url = location
                        continue
                
                return (resp.status, body, resp_headers, str(resp.url))
        
        return (302, "Too many redirects", {}, current_url)
    
    async def post(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Tuple[int, str, Dict[str, str], Dict[str, str]]:
        """
        Perform POST request with retry mechanism
        
        Args:
            url: Target URL
            headers: Additional headers
            json_data: JSON body
            data: Form data
            
        Returns:
            Tuple of (status_code, body, cookies, headers)
        """
        request_headers = self._build_headers(headers)
        retries = 0
        
        while retries <= self.max_retries:
            try:
                if not self.session:
                    raise RuntimeError("HTTPClient session not initialized")
                
                async with self.session.post(
                    url,
                    headers=request_headers,
                    json=json_data,
                    data=data
                ) as resp:
                    body = await resp.text()
                    resp_headers = dict(resp.headers)
                    
                    # Extract cookies
                    cookies = {}
                    for cookie in resp.cookies.items():
                        cookies[cookie[0]] = cookie[1]
                    
                    return (resp.status, body, cookies, resp_headers)
                    
            except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                retries += 1
                if retries > self.max_retries:
                    return (408 if isinstance(e, asyncio.TimeoutError) else 500,
                            str(e), {}, {})
                
                # Wait before retry (exponential backoff)
                await asyncio.sleep(0.5 * retries)
        
        return (500, "Max retries exceeded", {}, {})
