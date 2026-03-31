# GCP Orchestration MVP - Backlog

## Business & Legal
- [ ] Determine payment channel / gateway.
  - *Insight*: Stripe Billing is the industry standard for metered usage, but consider a Merchant of Record (MoR) like Lemon Squeezy or Paddle. MoRs automatically handle global tax/VAT compliance, which removes a massive legal and accounting burden for an early-stage MVP.
- [ ] Form an LLC and determine tax status and implications.
  - *Insight*: Services like Stripe Atlas or Clerky make this seamless. If bootstrapping and optimizing for simplicity, a standard LLC (pass-through taxation) is ideal. If you plan to raise venture capital later, a Delaware C-Corp is standard but comes with more overhead.
- [ ] Establish a path to SOC 2 Compliance (Platform & Tenants).
  - *Insight (Platform)*: Achieving SOC 2 Type II for the orchestration platform requires strict IAM boundaries, centralized audit logging (GCP Cloud Audit Logs exported to a locked BigQuery/GCS bucket), mandatory MFA for all platform engineers, and automated vulnerability scanning (Google Artifact Registry natively does this). Tools like Vanta or Drata can automate evidence collection directly from GCP.
  - *Insight (Tenants)*: To allow users to build SOC 2 compliant apps *on top* of the platform, the orchestration engine must generate infrastructure that is "compliant by default". This means: 1) Forcing VPC Service Controls around sensitive data (e.g., Cloud SQL). 2) Disabling public IP generation on databases. 3) Enforcing encryption-at-rest with Customer-Managed Encryption Keys (CMEK) via Cloud KMS. 4) Provisioning default IAM roles with least-privilege (e.g., a Cloud Run service account should only have `roles/cloudsql.client` and nothing else).

## Billing & Infrastructure Strategy
- [ ] Implement a mechanism to bill users based on their project's resource usage.
  - *Insight*: Usage-based billing requires airtight observability. Enforce a strict labeling policy (e.g., `tenant_id:<uuid>`) on *every* generated GCP resource. You can export GCP Billing data natively to BigQuery, query the usage per tenant, and sync those aggregates to your billing provider (like Stripe's Metered Billing API) on a cron schedule.
- [ ] Implement an Internal AI Gateway for Agent Token Billing
  - *Insight*: To track and bill LLM usage per user, deploy an internal reverse proxy (e.g., Cloudflare AI Gateway or a custom Cloud Run service) in the Host Project. GSD agents send API calls to this proxy, which injects the master Anthropic key, logs input/output tokens + `tenant_id` to BigQuery, and routes the request. A cron job then aggregates these tokens, applies platform markup, and pushes the cost to Stripe Metered Billing.
- [ ] Determine the most cost-effective approach for provisioning infrastructure and deploying containers (evaluate Google Cloud Build vs. alternative setups to minimize costs).
  - *Insight*: For deployments, Cloud Run is the ultimate MVP target because its scale-to-zero capability avoids the baseline costs of an idle GKE cluster. For the build pipeline, Cloud Build is convenient but charges per minute. A cheaper alternative is using GitHub Actions (free tier) or a self-hosted runner on a GCP Spot VM, pushing container images directly to Google Artifact Registry.

## Technical & Architecture
- [ ] Build the GSD Agent Execution Engine
  - *Insight*: Coding agents MUST run in the Platform Host Project (Control Plane), never in the client's isolated project. When a build is triggered, the platform spins up an ephemeral Cloud Run Job containing the GSD CLI, Node.js, and Git. It securely pulls the user's workspace, executes the `/gsd` loop, pushes the code, and shuts down immediately, ensuring you only pay for active execution time while maintaining strict zero-trust isolation from client production environments.
- [ ] Provision Platform-Managed Git Persistence
  - *Insight*: The GSD framework relies strictly on atomic Git commits for context management. The platform must silently manage a Git repository for every standard project (via a platform-owned GitHub Org or self-hosted Gitea). For Enterprise users, support OAuth integration to commit directly to their BYO repositories.
- [ ] Implement Multi-Tenant Resource Abstraction (Standard vs. Enterprise)
  - *Insight*: The user experience completely abstracts GCP. For the vast majority of users (Standard/Pro tiers), their infrastructure runs as isolated services *within our internal platform GCP accounts* under strict tenant-level IAM labeling/boundaries. Only "Enterprise" users unlock the "BYO Project" (Bring Your Own Project) capability, where our orchestrator deploys Terraform directly into the customer's privately owned GCP organization.
- [ ] Refine the node link system (Full-Stack Data Contract DAG):
  - [ ] Ensure the registry accounts for all possible links.
  - [ ] Ensure the UI supports interfacing with the link system.
  - *Insight (Infrastructure)*: If "nodes" represent services (e.g., Web -> API -> Database), you are essentially building a Directed Acyclic Graph (DAG). Consider generating Terraform/OpenTofu configurations programmatically and letting the IaC tool resolve the dependency tree. For the frontend UI, libraries like React Flow are purpose-built for visual node-linking interfaces.
  - *Insight (Code & Schema Dependency)*: Expand the DAG to track deep **Data Contracts**. Allow the creation of Firebase/Database Schema Nodes that define sub-collections and exact fields. When linking a Container Node to a Schema Node, require the user/agent to define the specific *fields* the container Reads or Writes. This creates a deterministic dependency graph across both infrastructure AND code logic. If a field name is changed in the Schema Node, the graph can instantly flag upstream/downstream Container Nodes with "Breaking Contract" alerts before deployment.
- [ ] Orchestrate Database Schema Migrations & Versioning
  - *Insight*: Because the DAG tracks schema state (V1 vs. V2), the orchestration engine must handle the transition between these states when users promote from Dev -> Staging -> Prod. The platform should orchestrate migration execution natively. For SQL databases, this means securely running `prisma migrate deploy` (or Flyway/Alembic) as a short-lived Cloud Run Job *before* routing traffic to the new compute containers. For NoSQL (Firebase), this means orchestrating background backfill/update scripts to ensure data integrity without downtime.
- [ ] Single Pane of Glass: Deployment Oversight & Observability
  - *Insight*: Because GCP is abstracted away, the platform *must* natively surface all operational data. 
    1. **Deployment Verification**: Tap into the Cloud Run and Cloud Build APIs to stream rollout status, catching crash loops or failed health checks instantly.
    2. **Metrics & Stats**: Query the GCP Cloud Monitoring API to overlay real-time stats (CPU/Memory utilization, Request Latency p95, 5xx error rates) directly onto the Container Nodes in the UI.
    3. **Logs**: Integrate the GCP Cloud Logging API to stream stdout/stderr from containers directly to a terminal pane in the platform.
    4. **Uptime**: Programmatically provision GCP Uptime Checks to ping the user's custom domains and alert them on downtime.
- [ ] Manage Secret Provisioning and Access
  - *Insight*: Secrets should be provisioned **per user project**, not in the shared platform host. Storing all tenants' secrets (database passwords, API keys) in a central Platform Secret Manager creates a massive single point of failure and violates strict multi-tenant isolation. By placing them in the isolated Dev/Staging/Prod projects, you leverage GCP's native IAM boundaries (the Dev Cloud Run instance can only physically read the Dev Secret Manager) and simplify tear-down when a user deletes an environment.
- [ ] Custom Domains & CDN:
  - [ ] Allow provisioning of SSL certificates.
  - [ ] Configure CDN for user projects.
  - [ ] Support pointing to users' custom domains.
  - *Insight*: A "Shared Platform Host Project" architecture is optimal here. Your platform owns a single Global External Application Load Balancer in the host project, aggregating all traffic and completely eliminating the $18/mo base cost for individual customers. You can use GCP Certificate Manager to dynamically attach thousands of customer domains to this single entry point. The load balancer then routes traffic down to the isolated customer projects using Cross-Project Serverless NEGs. Note: Because of state lock collisions, update the Host's URL Maps and certificates dynamically via the GCP API, rather than via Terraform, while keeping the isolated environment infrastructure fully managed by Terraform.