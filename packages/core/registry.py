"""Component registry — single source of truth for all component types."""

from dataclasses import dataclass, field
from pydantic import BaseModel

from packages.core.schemas.enums import NodeType, COMPUTE_TYPES
from packages.core.schemas.configs import TYPE_TO_CONFIG


@dataclass(frozen=True)
class ComponentDefinition:
    node_type: NodeType
    label: str
    category: str
    is_compute: bool
    config_model: type[BaseModel] | None
    terraform_resource: str
    iam_scope: str | None = None
    iam_terraform_resource: str | None = None
    default_outputs: tuple[dict, ...] = ()


REGISTRY: dict[NodeType, ComponentDefinition] = {
    NodeType.SERVICE_ACCOUNT: ComponentDefinition(
        node_type=NodeType.SERVICE_ACCOUNT,
        label="Service Account",
        category="Identity",
        is_compute=False,
        config_model=TYPE_TO_CONFIG[NodeType.SERVICE_ACCOUNT],
        terraform_resource="google_service_account",
        default_outputs=(
            {"name": "email", "type": "connection_string"},
            {"name": "unique_id", "type": "connection_string"},
            {"name": "name", "type": "connection_string"},
        ),
    ),
    NodeType.VPC: ComponentDefinition(
        node_type=NodeType.VPC,
        label="VPC",
        category="Network",
        is_compute=False,
        config_model=TYPE_TO_CONFIG[NodeType.VPC],
        terraform_resource="google_compute_network",
        default_outputs=(
            {"name": "self_link", "type": "self_link"},
            {"name": "id", "type": "connection_string"},
            {"name": "name", "type": "connection_string"},
        ),
    ),
    NodeType.SUBNET: ComponentDefinition(
        node_type=NodeType.SUBNET,
        label="Subnet",
        category="Network",
        is_compute=False,
        config_model=TYPE_TO_CONFIG[NodeType.SUBNET],
        terraform_resource="google_compute_subnetwork",
        default_outputs=(
            {"name": "self_link", "type": "self_link"},
            {"name": "id", "type": "connection_string"},
            {"name": "gateway_address", "type": "ip_address"},
        ),
    ),
    NodeType.VPC_CONNECTOR: ComponentDefinition(
        node_type=NodeType.VPC_CONNECTOR,
        label="VPC Connector",
        category="Network",
        is_compute=False,
        config_model=TYPE_TO_CONFIG[NodeType.VPC_CONNECTOR],
        terraform_resource="google_vpc_access_connector",
        default_outputs=(
            {"name": "id", "type": "connection_string"},
            {"name": "self_link", "type": "self_link"},
            {"name": "state", "type": "connection_string"},
        ),
    ),
    NodeType.SECRET_MANAGER: ComponentDefinition(
        node_type=NodeType.SECRET_MANAGER,
        label="Secret Manager",
        category="Security",
        is_compute=False,
        config_model=TYPE_TO_CONFIG[NodeType.SECRET_MANAGER],
        terraform_resource="google_secret_manager_secret",
        iam_scope="resource",
        iam_terraform_resource="google_secret_manager_secret_iam_member",
        default_outputs=(
            {"name": "secret_id", "type": "connection_string"},
            {"name": "version", "type": "connection_string"},
            {"name": "name", "type": "connection_string"},
        ),
    ),
    NodeType.GCS_BUCKET: ComponentDefinition(
        node_type=NodeType.GCS_BUCKET,
        label="GCS Bucket",
        category="Storage",
        is_compute=False,
        config_model=TYPE_TO_CONFIG[NodeType.GCS_BUCKET],
        terraform_resource="google_storage_bucket",
        iam_scope="resource",
        iam_terraform_resource="google_storage_bucket_iam_member",
        default_outputs=(
            {"name": "bucket", "type": "bucket"},
            {"name": "url", "type": "connection_string"},
            {"name": "self_link", "type": "self_link"},
        ),
    ),
    NodeType.CLOUD_SQL: ComponentDefinition(
        node_type=NodeType.CLOUD_SQL,
        label="Cloud SQL",
        category="Data",
        is_compute=False,
        config_model=TYPE_TO_CONFIG[NodeType.CLOUD_SQL],
        terraform_resource="google_sql_database_instance",
        iam_scope="project",
        iam_terraform_resource="google_project_iam_member",
        default_outputs=(
            {"name": "connection_name", "type": "connection_string"},
            {"name": "private_ip", "type": "ip_address"},
            {"name": "self_link", "type": "self_link"},
        ),
    ),
    NodeType.FIRESTORE: ComponentDefinition(
        node_type=NodeType.FIRESTORE,
        label="Firestore",
        category="Data",
        is_compute=False,
        config_model=TYPE_TO_CONFIG[NodeType.FIRESTORE],
        terraform_resource="google_firestore_database",
        iam_scope="project",
        iam_terraform_resource="google_project_iam_member",
        default_outputs=(
            {"name": "database", "type": "connection_string"},
            {"name": "name", "type": "connection_string"},
        ),
    ),
    NodeType.BIGQUERY: ComponentDefinition(
        node_type=NodeType.BIGQUERY,
        label="BigQuery",
        category="Data",
        is_compute=False,
        config_model=TYPE_TO_CONFIG[NodeType.BIGQUERY],
        terraform_resource="google_bigquery_dataset",
        iam_scope="dataset",
        iam_terraform_resource="google_bigquery_dataset_iam_member",
        default_outputs=(
            {"name": "dataset", "type": "dataset"},
        ),
    ),
    NodeType.BIGTABLE: ComponentDefinition(
        node_type=NodeType.BIGTABLE,
        label="Bigtable",
        category="Data",
        is_compute=False,
        config_model=TYPE_TO_CONFIG[NodeType.BIGTABLE],
        terraform_resource="google_bigtable_instance",
        iam_scope="project",
        iam_terraform_resource="google_project_iam_member",
        default_outputs=(
            {"name": "instance", "type": "connection_string"},
        ),
    ),
    NodeType.PUBSUB_SCHEMA: ComponentDefinition(
        node_type=NodeType.PUBSUB_SCHEMA,
        label="Pub/Sub Schema",
        category="Messaging",
        is_compute=False,
        config_model=TYPE_TO_CONFIG[NodeType.PUBSUB_SCHEMA],
        terraform_resource="google_pubsub_schema",
        default_outputs=(
            {"name": "name", "type": "connection_string"},
            {"name": "id", "type": "connection_string"},
        ),
    ),
    NodeType.PUBSUB_TOPIC: ComponentDefinition(
        node_type=NodeType.PUBSUB_TOPIC,
        label="Pub/Sub Topic",
        category="Messaging",
        is_compute=False,
        config_model=TYPE_TO_CONFIG[NodeType.PUBSUB_TOPIC],
        terraform_resource="google_pubsub_topic",
        iam_scope="resource",
        iam_terraform_resource="google_pubsub_topic_iam_member",
        default_outputs=(
            {"name": "topic", "type": "topic"},
            {"name": "id", "type": "connection_string"},
        ),
    ),
    NodeType.PUBSUB_SUBSCRIPTION: ComponentDefinition(
        node_type=NodeType.PUBSUB_SUBSCRIPTION,
        label="Pub/Sub Subscription",
        category="Messaging",
        is_compute=False,
        config_model=TYPE_TO_CONFIG[NodeType.PUBSUB_SUBSCRIPTION],
        terraform_resource="google_pubsub_subscription",
        iam_scope="resource",
        iam_terraform_resource="google_pubsub_subscription_iam_member",
        default_outputs=(
            {"name": "subscription", "type": "connection_string"},
            {"name": "id", "type": "connection_string"},
        ),
    ),
    NodeType.CLOUD_TASK_QUEUE: ComponentDefinition(
        node_type=NodeType.CLOUD_TASK_QUEUE,
        label="Cloud Tasks Queue",
        category="Messaging",
        is_compute=False,
        config_model=TYPE_TO_CONFIG[NodeType.CLOUD_TASK_QUEUE],
        terraform_resource="google_cloud_tasks_queue",
        iam_scope="resource",
        iam_terraform_resource="google_cloud_tasks_queue_iam_member",
        default_outputs=(
            {"name": "queue", "type": "queue"},
            {"name": "id", "type": "connection_string"},
        ),
    ),
    NodeType.CLOUD_RUN: ComponentDefinition(
        node_type=NodeType.CLOUD_RUN,
        label="Cloud Run",
        category="Compute",
        is_compute=True,
        config_model=TYPE_TO_CONFIG[NodeType.CLOUD_RUN],
        terraform_resource="google_cloud_run_v2_service",
        iam_scope="resource",
        iam_terraform_resource="google_cloud_run_v2_service_iam_member",
        default_outputs=(
            {"name": "endpoint", "type": "http_endpoint"},
            {"name": "name", "type": "connection_string"},
            {"name": "latest_revision", "type": "connection_string"},
        ),
    ),
    NodeType.CLOUD_RUN_JOB: ComponentDefinition(
        node_type=NodeType.CLOUD_RUN_JOB,
        label="Cloud Run Job",
        category="Compute",
        is_compute=True,
        config_model=TYPE_TO_CONFIG[NodeType.CLOUD_RUN_JOB],
        terraform_resource="google_cloud_run_v2_job",
        iam_scope="project",
        iam_terraform_resource="google_project_iam_member",
        default_outputs=(
            {"name": "job_name", "type": "connection_string"},
            {"name": "id", "type": "connection_string"},
        ),
    ),
    NodeType.CLOUD_FUNCTION: ComponentDefinition(
        node_type=NodeType.CLOUD_FUNCTION,
        label="Cloud Function",
        category="Compute",
        is_compute=True,
        config_model=TYPE_TO_CONFIG[NodeType.CLOUD_FUNCTION],
        terraform_resource="google_cloudfunctions2_function",
        iam_scope="resource",
        iam_terraform_resource="google_cloudfunctions2_function_iam_member",
        default_outputs=(
            {"name": "endpoint", "type": "http_endpoint"},
            {"name": "name", "type": "connection_string"},
        ),
    ),
    NodeType.EXTERNAL_LB: ComponentDefinition(
        node_type=NodeType.EXTERNAL_LB,
        label="External LB",
        category="Network",
        is_compute=False,
        config_model=TYPE_TO_CONFIG[NodeType.EXTERNAL_LB],
        terraform_resource="google_compute_global_address",
        default_outputs=(
            {"name": "ip_address", "type": "ip_address"},
            {"name": "self_link", "type": "self_link"},
        ),
    ),
    NodeType.CLOUD_DNS: ComponentDefinition(
        node_type=NodeType.CLOUD_DNS,
        label="Cloud DNS",
        category="Network",
        is_compute=False,
        config_model=TYPE_TO_CONFIG[NodeType.CLOUD_DNS],
        terraform_resource="google_dns_managed_zone",
        default_outputs=(
            {"name": "name_servers", "type": "connection_string"},
            {"name": "dns_name", "type": "connection_string"},
        ),
    ),
    NodeType.THIRD_PARTY_API: ComponentDefinition(
        node_type=NodeType.THIRD_PARTY_API,
        label="3rd Party API",
        category="External",
        is_compute=False,
        config_model=TYPE_TO_CONFIG[NodeType.THIRD_PARTY_API],
        terraform_resource="",
        default_outputs=(
            {"name": "endpoint", "type": "http_endpoint"},
        ),
    ),

    # --- Child Data Nodes (Phase 5) -------------------------------------------
    NodeType.FIRESTORE_COLLECTION: ComponentDefinition(
        node_type=NodeType.FIRESTORE_COLLECTION,
        label="Firestore Collection",
        category="Data",
        is_compute=False,
        config_model=TYPE_TO_CONFIG[NodeType.FIRESTORE_COLLECTION],
        terraform_resource="",
        default_outputs=(),
    ),
    NodeType.BIGQUERY_TABLE: ComponentDefinition(
        node_type=NodeType.BIGQUERY_TABLE,
        label="BigQuery Table",
        category="Data",
        is_compute=False,
        config_model=TYPE_TO_CONFIG[NodeType.BIGQUERY_TABLE],
        terraform_resource="google_bigquery_table",
        default_outputs=(
            {"name": "table_id", "type": "table"},
        ),
    ),
    NodeType.CLOUD_SQL_DATABASE: ComponentDefinition(
        node_type=NodeType.CLOUD_SQL_DATABASE,
        label="Cloud SQL Database",
        category="Data",
        is_compute=False,
        config_model=TYPE_TO_CONFIG[NodeType.CLOUD_SQL_DATABASE],
        terraform_resource="google_sql_database",
        default_outputs=(
            {"name": "name", "type": "connection_string"},
        ),
    ),
    NodeType.CLOUD_SQL_TABLE: ComponentDefinition(
        node_type=NodeType.CLOUD_SQL_TABLE,
        label="Cloud SQL Table",
        category="Data",
        is_compute=False,
        config_model=TYPE_TO_CONFIG[NodeType.CLOUD_SQL_TABLE],
        terraform_resource="",
        default_outputs=(),
    ),
}


def get_definition(node_type: NodeType) -> ComponentDefinition:
    return REGISTRY[node_type]


def get_config_model(node_type: NodeType) -> type[BaseModel] | None:
    return REGISTRY[node_type].config_model


def is_compute(node_type: NodeType) -> bool:
    return node_type in COMPUTE_TYPES
