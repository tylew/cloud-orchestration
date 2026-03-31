from pydantic import BaseModel


class LbSslPolicy(BaseModel):
    min_tls_version: str = "TLS_1_2"
    profile: str = "MODERN"


class LbManagedSslCertificate(BaseModel):
    domains: list[str]


class LbDefaultBackend(BaseModel):
    type: str = "serverless_neg"
    cloud_run_service: str | None = None
    region: str | None = None


class LbNegativeCachingPolicy(BaseModel):
    code: int
    ttl: str


class LbCdnPolicy(BaseModel):
    cache_mode: str = "CACHE_ALL_STATIC"
    default_ttl: str | None = None
    max_ttl: str | None = None
    client_ttl: str | None = None
    negative_caching: bool = True
    negative_caching_policy: list[LbNegativeCachingPolicy] = []
    serve_while_stale: int | None = None
    signed_url_cache_max_age: str | None = None


class LbLogging(BaseModel):
    enable: bool = True
    sample_rate: float = 1.0


class LbIap(BaseModel):
    oauth2_client_id: str
    oauth2_client_secret: str


class ExternalLbConfig(BaseModel):
    scheme: str = "EXTERNAL_MANAGED"
    ssl_policy: LbSslPolicy | None = None
    managed_ssl_certificate: LbManagedSslCertificate | None = None
    custom_ssl_certificate: str | None = None
    default_backend: LbDefaultBackend | None = None
    cdn_policy: LbCdnPolicy | None = None
    security_policy: str | None = None
    logging: LbLogging | None = None
    custom_request_headers: list[str] = []
    custom_response_headers: list[str] = []
    iap: LbIap | None = None
    # Legacy flat fields
    domain: str | None = None
    ssl: bool = True
    backend_service: str | None = None
    cdn_enabled: bool = False
    cloud_armor_policy: str | None = None
