import yaml
from pathlib import Path


class Config:
    def __init__(self, config_path: str = "config.yaml"):
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(path) as f:
            self._config = yaml.safe_load(f)

    @property
    def innago_api_url(self) -> str:
        return self._config["innago"]["api_url"]

    @property
    def innago_api_key(self) -> str:
        return self._config["innago"]["api_key"]

    @property
    def innago_property_id(self) -> str:
        return self._config["innago"]["property_id"]

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

    @property
    def email_from(self) -> str:
        return self._config.get("email", {}).get("from", "")

    @property
    def email_smtp_host(self) -> str:
        return self._config.get("email", {}).get("smtp_host", "")

    @property
    def email_smtp_port(self) -> int:
        return self._config.get("email", {}).get("smtp_port", 587)

    @property
    def email_smtp_user(self) -> str:
        return self._config.get("email", {}).get("smtp_user", "")

    @property
    def email_smtp_pass(self) -> str:
        return self._config.get("email", {}).get("smtp_pass", "")

    @property
    def packages(self) -> list:
        return self._config["packages"]

    @property
    def default_package(self) -> dict:
        for pkg in self.packages:
            if pkg.get("default"):
                return pkg
        return self.packages[0]

    @property
    def internet_keywords(self) -> list:
        return self._config.get("keywords", {}).get("internet_issues", [])

    @property
    def upgrade_keywords(self) -> list:
        return self._config.get("keywords", {}).get("upgrade_requests", [])

    @property
    def polling_interval(self) -> int:
        return self._config.get("polling", {}).get("interval_minutes", 5)
