import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RuntimeConfig:
    """Dynamic configuration backed by environment variables with optional runtime overrides for demo convenience."""

    _override_fault_mode: Optional[str] = field(default=None, init=False)
    _override_db_max_connections: Optional[int] = field(default=None, init=False)
    _override_payment_gateway_url: Optional[str] = field(default=None, init=False)
    _override_app_version: Optional[str] = field(default=None, init=False)

    @property
    def app_version(self) -> str:
        if self._override_app_version is not None:
            return self._override_app_version
        return os.getenv("APP_VERSION", "1.1.0-stable")

    @property
    def fault_mode(self) -> str:
        if self._override_fault_mode is not None:
            return self._override_fault_mode
        mode = os.getenv("FAULT_MODE", "none").strip().lower()
        if mode not in {"none", "bad_config", "bad_release", "high_latency"}:
            return "none"
        return mode

    @property
    def db_max_connections(self) -> int:
        if self._override_db_max_connections is not None:
            return self._override_db_max_connections
        raw = os.getenv("DB_MAX_CONNECTIONS", "50")
        try:
            return int(raw)
        except ValueError:
            return 0

    @property
    def payment_gateway_url(self) -> str:
        if self._override_payment_gateway_url is not None:
            return self._override_payment_gateway_url
        return os.getenv("PAYMENT_GATEWAY_URL", "https://payments.contoso.internal/v2/charge")

    @property
    def is_config_broken(self) -> bool:
        return (
            self.fault_mode == "bad_config"
            or self.db_max_connections <= 0
            or "invalid" in self.payment_gateway_url.lower()
            or "deprecated" in self.payment_gateway_url.lower()
        )

    @property
    def is_release_broken(self) -> bool:
        return self.fault_mode == "bad_release" or "buggy" in self.app_version.lower()

    def apply_preset(self, mode: str) -> None:
        mode = mode.strip().lower()
        if mode == "none":
            self._override_fault_mode = "none"
            self._override_db_max_connections = 50
            self._override_payment_gateway_url = "https://payments.contoso.internal/v2/charge"
            self._override_app_version = "1.1.0-stable"
        elif mode == "bad_config":
            self._override_fault_mode = "bad_config"
            self._override_db_max_connections = 0
            self._override_payment_gateway_url = "https://deprecated-v1.payments.contoso.invalid/charge"
        elif mode == "bad_release":
            self._override_fault_mode = "bad_release"
            self._override_app_version = "1.2.0-buggy"
        elif mode == "high_latency":
            self._override_fault_mode = "high_latency"
        else:
            raise ValueError(f"Unsupported fault mode: {mode}")

    def reset_to_env(self) -> None:
        self._override_fault_mode = None
        self._override_db_max_connections = None
        self._override_payment_gateway_url = None
        self._override_app_version = None

    def to_dict(self) -> dict:
        return {
            "app_version": self.app_version,
            "fault_mode": self.fault_mode,
            "db_max_connections": self.db_max_connections,
            "payment_gateway_url": self.payment_gateway_url,
            "is_config_broken": self.is_config_broken,
            "is_release_broken": self.is_release_broken,
            "appinsights_configured": bool(os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")),
        }


runtime_config = RuntimeConfig()
