"""
Configuration loader for Victorian Village integration.
"""

import yaml
from pathlib import Path


class Config:
    def __init__(self, config_path: str = "config.yaml"):
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(path) as f:
            self._config = yaml.safe_load(f)

    # Innago
    @property
    def innago_api_url(self) -> str:
        return self._config["innago"]["api_url"]

    @property
    def innago_api_key(self) -> str:
        return self._config["innago"]["api_key"]

    @property
    def innago_property_id(self) -> str:
        return self._config["innago"]["property_id"]

    # UISP
    @property
    def uisp_host(self) -> str:
        return self._config["uisp"]["host"]

    @property
    def uisp_crm_api_key(self) -> str:
        return self._config["uisp"]["crm_api_key"]

    @property
    def uisp_nms_api_key(self) -> str:
        return self._config["uisp"]["nms_api_key"]

    @property
    def uisp_parent_site_id(self) -> str:
        return self._config["uisp"]["parent_site_id"]

    # Billing
    @property
    def base_rate(self) -> float:
        return self._config.get("billing", {}).get("base_rate", 45)

    @property
    def total_units(self) -> int:
        return self._config.get("billing", {}).get("total_units", 118)

    @property
    def grace_period_day(self) -> int:
        return self._config.get("billing", {}).get("grace_period_day", 5)

    @property
    def complex_billing_email(self) -> str:
        return self._config.get("billing", {}).get("complex_email", "")

    # Packages / Service Plans
    @property
    def packages(self) -> list:
        return self._config.get("packages", [])

    @property
    def default_package(self) -> dict:
        for pkg in self.packages:
            if pkg.get("default"):
                return pkg
        return self.packages[0] if self.packages else {}

    def get_package_by_name(self, name: str) -> dict | None:
        for pkg in self.packages:
            if pkg["name"] == name:
                return pkg
        return None

    # Keywords for ticket forwarding
    @property
    def internet_keywords(self) -> list:
        return self._config.get("keywords", {}).get("internet_issues", [])

    # Polling
    @property
    def polling_interval(self) -> int:
        return self._config.get("polling", {}).get("interval_minutes", 5)
