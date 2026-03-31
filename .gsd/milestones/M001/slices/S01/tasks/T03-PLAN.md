---
estimated_steps: 1
estimated_files: 9
skills_used: []
---

# T03: Audit & update Messaging types (PubSub Topic, PubSub Subscription, PubSub Schema, Cloud Tasks Queue)

Use Terraform MCP to pull full specs for google_pubsub_topic, google_pubsub_subscription, google_pubsub_schema, google_cloud_tasks_queue. Compare against existing schemas. PubSub Schema and Cloud Tasks are currently thin (~3 and ~18 lines). Expect significant gaps.

## Inputs

- `Terraform MCP specs for 4 messaging resources`

## Expected Output

- `Updated schemas and templates for 4 messaging types`
- `New tests`

## Verification

pytest packages/tests/test_terraform.py -v
