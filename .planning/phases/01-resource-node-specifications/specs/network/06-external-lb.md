# External LB - Specifics

**Node type:** `external_lb`
**Terraform resource:** `google_compute_global_address` (base resource -- see composite nature below)
**Category:** Network
**IAM scope:** None

---

## Overview

External LB is a **composite resource** -- the most complex node type in the platform. While the REGISTRY maps it to `google_compute_global_address`, the actual load balancer requires 6-7 Terraform resources working together. Each sub-resource has its own lifecycle, mutability characteristics, and failure modes.

This complexity has significant implications for the deploy engine (Phase 3-5) and networking architecture (Phase 7).

## Composite Sub-Resource Map

The `external_lb.tf.j2` template generates the following Terraform resources:

| # | Sub-Resource | TF Resource | Created When | Depends On |
|---|-------------|-------------|-------------|------------|
| 1 | Static IP | `google_compute_global_address` | Always | -- |
| 2 | SSL Certificate | `google_compute_managed_ssl_certificate` | When `managed_ssl_certificate` is set | -- |
| 3 | Serverless NEG | `google_compute_region_network_endpoint_group` | When `default_backend` is set | Backend Cloud Run service |
| 4 | Backend Service | `google_compute_backend_service` | Always | Serverless NEG (#3) |
| 5 | URL Map | `google_compute_url_map` | Always | Backend Service (#4) |
| 6 | HTTPS Proxy | `google_compute_target_https_proxy` | Always | URL Map (#5), SSL Cert (#2) |
| 7 | Forwarding Rule | `google_compute_global_forwarding_rule` | Always | HTTPS Proxy (#6), Static IP (#1) |

### Internal dependency chain

```
Static IP (#1) ----+
                    |
                    v
SSL Cert (#2) --> HTTPS Proxy (#6) --> Forwarding Rule (#7)
                    ^
                    |
URL Map (#5) -------+
    ^
    |
Backend Service (#4)
    ^
    |
Serverless NEG (#3)
    ^
    |
Cloud Run Service (external reference)
```

## Per-Sub-Resource Mutability

### 1. google_compute_global_address (Static IP)

| Field | Mutable | Notes |
|-------|---------|-------|
| name | No (ForceNew) | Identity field |
| address_type | No (ForceNew) | EXTERNAL (default for global) |
| ip_version | No (ForceNew) | IPV4 or IPV6 |

The static IP is largely immutable. Once created, the IP address is fixed. This is intentional -- DNS records point to this IP, and changing it would break all external traffic.

### 2. google_compute_managed_ssl_certificate

| Field | Mutable | Notes |
|-------|---------|-------|
| name | No (ForceNew) | Identity field |
| managed.domains | **No (ForceNew)** | **Changing domains recreates the certificate** |

**Critical gotcha:** Changing the `domains` list triggers SSL certificate recreation. Google-managed SSL certificate provisioning takes **15-60 minutes** (DNS validation, certificate issuance). During this window, HTTPS traffic may fail or show certificate errors.

**Platform UX:** Show a strong warning when domains change. Consider supporting certificate pre-provisioning (create new cert before destroying old).

### 3. google_compute_region_network_endpoint_group (Serverless NEG)

| Field | Mutable | Notes |
|-------|---------|-------|
| name | No (ForceNew) | Identity field |
| network_endpoint_type | No (ForceNew) | Always `SERVERLESS` |
| region | No (ForceNew) | Must match Cloud Run service region |
| cloud_run.service | Yes | Can point to different Cloud Run service |

The NEG is the bridge between the LB and Cloud Run. It references a Cloud Run service by name. The service reference can be changed without recreating the NEG.

### 4. google_compute_backend_service

| Field | Mutable | Notes |
|-------|---------|-------|
| name | No (ForceNew) | Identity field |
| backend (list) | Yes | Can add/remove backends and change weights |
| cdn_policy | Yes | Full CDN configuration is mutable |
| security_policy | Yes | Cloud Armor policy reference |
| log_config | Yes | Logging enable/disable and sampling |
| iap | Yes | Identity-Aware Proxy configuration |
| custom_request_headers | Yes | Request header manipulation |
| custom_response_headers | Yes | Response header manipulation |

The backend service is the **most mutable** sub-resource. Most operational changes (traffic weights, CDN, security, logging) only affect this resource.

### 5. google_compute_url_map

| Field | Mutable | Notes |
|-------|---------|-------|
| name | No (ForceNew) | Identity field |
| default_service | Yes | Can change the default backend |
| host_rule, path_matcher | Yes | URL routing rules are fully mutable |

The current template uses a simple URL map (all traffic to one backend service). Advanced routing (multiple paths to different backends) would require extending the template.

### 6. google_compute_target_https_proxy

| Field | Mutable | Notes |
|-------|---------|-------|
| name | No (ForceNew) | Identity field |
| url_map | Yes | Can point to different URL map |
| ssl_certificates | Yes | Can swap certificates |

The HTTPS proxy terminates TLS. Certificate swaps are mutable (useful for certificate rotation).

### 7. google_compute_global_forwarding_rule

| Field | Mutable | Notes |
|-------|---------|-------|
| name | No (ForceNew) | Identity field |
| ip_address | No (ForceNew) | Bound to specific static IP |
| port_range | No (ForceNew) | Typically "443" |
| target | Yes | Can point to different proxy |
| load_balancing_scheme | No (ForceNew) | EXTERNAL_MANAGED or EXTERNAL |

The forwarding rule binds the IP address to the proxy. The IP address binding is permanent.

## ExternalLbConfig Field-to-Sub-Resource Mapping

| Config Field | Affects Sub-Resource(s) | Mutability |
|-------------|------------------------|------------|
| scheme | backend_service, forwarding_rule | ForceNew on forwarding_rule |
| ssl_policy | target_https_proxy | Mutable |
| managed_ssl_certificate.domains | managed_ssl_certificate | **ForceNew (15+ min reprovision)** |
| custom_ssl_certificate | target_https_proxy | Mutable |
| default_backend | serverless_neg, backend_service | NEG mostly ForceNew, backend mutable |
| cdn_policy | backend_service | Mutable |
| security_policy | backend_service | Mutable |
| logging | backend_service | Mutable |
| custom_request_headers | backend_service | Mutable |
| custom_response_headers | backend_service | Mutable |
| iap | backend_service | Mutable |

## Legacy Fields

The ExternalLbConfig includes 5 legacy flat fields that appear to be from an older schema version:

| Field | Legacy Purpose | Current Equivalent |
|-------|---------------|-------------------|
| domain | Single domain string | `managed_ssl_certificate.domains` |
| ssl | Enable/disable SSL | `managed_ssl_certificate` presence |
| backend_service | Backend reference | `default_backend.cloud_run_service` |
| cdn_enabled | CDN toggle | `cdn_policy` presence |
| cloud_armor_policy | Security policy | `security_policy` |

The REQUIRED_FIELDS validation requires `backend_service` (the legacy field). The structured equivalent (`default_backend`) should be used in new blueprints.

## Edge Cases

1. **SSL certificate provisioning delay:** Google-managed SSL certificates require DNS validation and can take 15-60 minutes. The first deploy of an External LB with managed SSL will block on certificate provisioning. The deploy engine should handle this with extended timeouts.

2. **Domain DNS requirement:** Managed SSL certificates require the domain to have a DNS A record pointing to the LB's static IP. DNS propagation can add additional delay. The platform could provide the static IP first (separate deploy step) to allow DNS setup before SSL provisioning.

3. **Multiple backends:** The current template supports a single backend (one Cloud Run service via one serverless NEG). Multi-backend LBs (traffic splitting across services, path-based routing) would require extending the template with multiple NEGs and URL map rules.

4. **CDN invalidation:** Enabling CDN (`cdn_policy`) is a mutable backend service change, but cached content is not automatically invalidated. Users may need to manually invalidate the CDN cache after deployments.

5. **IAP (Identity-Aware Proxy):** When `iap` is configured, the LB requires OAuth consent screen setup in the GCP project. This is a one-time manual step that cannot be automated via Terraform.

6. **Cloud Armor policy lifecycle:** The `security_policy` field references a Cloud Armor policy by name. The policy itself is not managed by the External LB node -- it must exist independently (potentially as a separate resource not yet in the platform's node types).

7. **Port 443 only:** The template hardcodes `port_range = "443"` on the forwarding rule. HTTP (port 80) to HTTPS redirect would require an additional forwarding rule and HTTP proxy (not currently in the template).

8. **Scheme change:** Changing between `EXTERNAL_MANAGED` and `EXTERNAL` affects the forwarding rule (ForceNew) and backend service behavior. This is a significant change that should be treated as a full LB rebuild.
