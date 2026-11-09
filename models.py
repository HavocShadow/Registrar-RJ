#!/usr/bin/env python3
"""
Data models for RegisV8
Uses dataclasses for cleaner code and better type hints
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List
from enum import Enum
import time


class MissionStatus(Enum):
    """Status of a registration mission"""
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"


@dataclass
class Config:
    """Application configuration"""
    timeout: int = 15
    retry: int = 3
    concurrency: int = 30
    user_agent: str = "Mozilla/5.0"
    delay: float = 0
    output_folder: str = "output"
    max_redirects: int = 5
    ssl_verify: bool = False


@dataclass
class Account:
    """
    Account information for registration
    
    Format accounts.txt (6 fields):
    username|password|fullname|banktype|bankname|banknumber
    
    Example:
    user01|password01|Andi Saputra|59|GOPAY|08123456789
    """
    username: str
    password: str
    fullname: str
    bank_type: str
    bank_name: str
    bank_number: str
    
    def is_valid(self) -> bool:
        """Validate account data"""
        return all([
            self.username,
            self.password,
            self.fullname,
            self.bank_type,
            self.bank_name,
            self.bank_number
        ])
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary (password masked)"""
        return {
            'username': self.username,
            'password': '***',
            'fullname': self.fullname,
            'bank_type': self.bank_type,
            'bank_name': self.bank_name,
            'bank_number': self.bank_number
        }
    
    def to_dict_full(self) -> Dict[str, str]:
        """Convert to dictionary with full data"""
        return asdict(self)


@dataclass
class Site:
    """Target website information"""
    url: str
    domain: str = ""
    
    def __post_init__(self):
        """Extract domain from URL"""
        if not self.domain and self.url:
            from urllib.parse import urlparse
            parsed = urlparse(self.url)
            self.domain = f"{parsed.scheme}://{parsed.netloc}"
    
    def is_valid(self) -> bool:
        """Validate site URL"""
        if not self.url:
            return False
        
        from urllib.parse import urlparse
        try:
            result = urlparse(self.url)
            return all([result.scheme, result.netloc])
        except:
            return False


@dataclass
class MissionResult:
    """Result of a single registration mission"""
    mission_id: int
    site_url: str
    account: str
    status: MissionStatus = MissionStatus.PENDING
    short_name: Optional[str] = None
    post_url: Optional[str] = None
    http_status_get: Optional[int] = None
    http_status_post: Optional[int] = None
    response_body: Optional[str] = None
    error_message: Optional[str] = None
    shortname_source: str = "unknown"
    execution_time: float = 0.0
    bank_type_used: Optional[str] = None
    bank_name_used: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'mission_id': self.mission_id,
            'site_url': self.site_url,
            'account': self.account,
            'status': self.status.value,
            'short_name': self.short_name,
            'post_url': self.post_url,
            'http_status_get': self.http_status_get,
            'http_status_post': self.http_status_post,
            'response_body': self.response_body[:500] if self.response_body else None,
            'error_message': self.error_message,
            'shortname_source': self.shortname_source,
            'execution_time': self.execution_time,
            'bank_type_used': self.bank_type_used,
            'bank_name_used': self.bank_name_used
        }


@dataclass
class MissionState:
    """Global state for tracking mission progress"""
    total_missions: int = 0
    completed_missions: int = 0
    success_count: int = 0
    failure_count: int = 0
    start_time: float = field(default_factory=time.time)
    active_missions: int = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.completed_missions == 0:
            return 0.0
        return (self.success_count / self.completed_missions) * 100
    
    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds"""
        return time.time() - self.start_time
    
    @property
    def avg_time_per_mission(self) -> float:
        """Get average time per mission"""
        if self.completed_missions == 0:
            return 0.0
        return self.elapsed_time / self.completed_missions
    
    @property
    def throughput(self) -> float:
        """Get requests per second"""
        if self.elapsed_time == 0:
            return 0.0
        return self.completed_missions / self.elapsed_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'total_missions': self.total_missions,
            'completed_missions': self.completed_missions,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'success_rate': self.success_rate,
            'elapsed_time': self.elapsed_time,
            'avg_time_per_mission': self.avg_time_per_mission,
            'throughput': self.throughput
        }
