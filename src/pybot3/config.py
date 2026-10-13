from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Settings:
    platform: str | None = None
    token: str | None = None
    log_level: str = "INFO"
    timeout: float = 30.0
    rate_limit: float = 0.0
    webhook_url: str | None = None
    webhook_secret: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_env(cls, prefix: str = "PYBOT3") -> "Settings":
        return cls(
            platform=os.getenv(f"{prefix}_PLATFORM"),
            token=os.getenv(f"{prefix}_TOKEN"),
            log_level=os.getenv(f"{prefix}_LOG_LEVEL", "INFO").upper(),
            timeout=float(os.getenv(f"{prefix}_TIMEOUT", "30")),
            rate_limit=float(os.getenv(f"{prefix}_RATE_LIMIT", "0")),
            webhook_url=os.getenv(f"{prefix}_WEBHOOK_URL"),
            webhook_secret=os.getenv(f"{prefix}_WEBHOOK_SECRET"),
            extra={k: v for k, v in os.environ.items() if k.startswith(f"{prefix}_")},
        )

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)


__all__ = ["Settings"]
