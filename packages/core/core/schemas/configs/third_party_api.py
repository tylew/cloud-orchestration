from pydantic import BaseModel


class ThirdPartyRateLimit(BaseModel):
    requests_per_second: int | None = None


class ThirdPartyApiConfig(BaseModel):
    provider: str
    base_url: str
    auth_method: str = "api_key"
    secret_ref: str | None = None
    rate_limit: ThirdPartyRateLimit | None = None
    timeout_ms: int | None = None
    description: str | None = None
