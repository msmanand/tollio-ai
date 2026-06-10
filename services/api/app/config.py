import os
from typing import List

from pydantic import BaseModel


class RuntimeConfig(BaseModel):
    google_maps_api_key: str = ""
    enable_live_routes: bool = False
    mongodb_uri: str = ""
    tollio_storage_mode: str = "mock"
    google_cloud_project: str = ""
    google_application_credentials: str = ""
    gemini_api_key: str = ""
    tollio_agent_mode: str = "mock"

    @property
    def google_routes_ready(self) -> bool:
        return self.enable_live_routes and bool(self.google_maps_api_key)

    @property
    def mongodb_ready(self) -> bool:
        return self.tollio_storage_mode == "mongodb" and bool(self.mongodb_uri)

    @property
    def gemini_ready(self) -> bool:
        return self.tollio_agent_mode == "live" and bool(self.gemini_api_key)

    @property
    def routes_mode(self) -> str:
        return "live" if self.google_routes_ready else "mock"

    @property
    def mongodb_mode(self) -> str:
        return "live" if self.mongodb_ready else "mock"

    @property
    def agent_mode(self) -> str:
        return "live" if self.gemini_ready else "mock"

    def warnings(self) -> List[str]:
        warnings = []
        if self.enable_live_routes and not self.google_maps_api_key:
            warnings.append("ENABLE_LIVE_ROUTES=true but GOOGLE_MAPS_API_KEY is missing.")
        if self.tollio_storage_mode == "mongodb" and not self.mongodb_uri:
            warnings.append("TOLLIO_STORAGE_MODE=mongodb but MONGODB_URI is missing.")
        if self.tollio_agent_mode == "live" and not self.gemini_api_key:
            warnings.append("TOLLIO_AGENT_MODE=live but GEMINI_API_KEY is missing.")
        return warnings


class SystemStatus(BaseModel):
    api_status: str
    routes_mode: str
    mongodb_mode: str
    agent_mode: str
    google_routes_ready: bool
    mongodb_ready: bool
    gemini_ready: bool
    warnings: List[str]


def get_runtime_config() -> RuntimeConfig:
    return RuntimeConfig(
        google_maps_api_key=os.getenv("GOOGLE_MAPS_API_KEY", "").strip(),
        enable_live_routes=_env_bool("ENABLE_LIVE_ROUTES"),
        mongodb_uri=os.getenv("MONGODB_URI", "").strip(),
        tollio_storage_mode=os.getenv("TOLLIO_STORAGE_MODE", "mock").strip().lower(),
        google_cloud_project=os.getenv("GOOGLE_CLOUD_PROJECT", "").strip(),
        google_application_credentials=os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip(),
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        tollio_agent_mode=os.getenv("TOLLIO_AGENT_MODE", "mock").strip().lower(),
    )


def get_system_status() -> SystemStatus:
    config = get_runtime_config()
    return SystemStatus(
        api_status="ok",
        routes_mode=config.routes_mode,
        mongodb_mode=config.mongodb_mode,
        agent_mode=config.agent_mode,
        google_routes_ready=config.google_routes_ready,
        mongodb_ready=config.mongodb_ready,
        gemini_ready=config.gemini_ready,
        warnings=config.warnings(),
    )


def _env_bool(name: str) -> bool:
    return os.getenv(name, "false").strip().lower() == "true"
