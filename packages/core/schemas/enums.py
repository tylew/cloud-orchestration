"""Enumerations derived from GCP_SCHEMA.md."""

from enum import StrEnum


class NodeType(StrEnum):
    SERVICE_ACCOUNT = "service_account"
    VPC = "vpc"
    SUBNET = "subnet"
    VPC_CONNECTOR = "vpc_connector"
    SECRET_MANAGER = "secret_manager"
    GCS_BUCKET = "gcs_bucket"
    CLOUD_SQL = "cloud_sql"
    FIRESTORE = "firestore"
    BIGQUERY = "bigquery"
    BIGTABLE = "bigtable"
    PUBSUB_SCHEMA = "pubsub_schema"
    PUBSUB_TOPIC = "pubsub_topic"
    PUBSUB_SUBSCRIPTION = "pubsub_subscription"
    CLOUD_TASK_QUEUE = "cloud_task_queue"
    CLOUD_RUN = "cloud_run"
    CLOUD_RUN_JOB = "cloud_run_job"
    CLOUD_FUNCTION = "cloud_function"
    EXTERNAL_LB = "external_lb"
    CLOUD_DNS = "cloud_dns"
    THIRD_PARTY_API = "third_party_api"
    # Child data node types (Phase 5)
    FIRESTORE_COLLECTION = "firestore_collection"
    BIGQUERY_TABLE = "bigquery_table"
    CLOUD_SQL_DATABASE = "cloud_sql_database"
    CLOUD_SQL_TABLE = "cloud_sql_table"


class ActionType(StrEnum):
    READ = "Read"
    WRITE = "Write"
    INVOKE = "Invoke"
    EMIT = "Emit"
    ENQUEUE = "Enqueue"
    DESCRIBE = "Describe"


class Protocol(StrEnum):
    HTTPS = "https"
    GRPC = "grpc"
    SQL = "sql"
    PUBSUB = "pubsub"
    TASK_QUEUE = "task_queue"
    BIGQUERY_API = "bigquery_api"
    BIGTABLE_API = "bigtable_api"
    FIRESTORE_API = "firestore_api"
    GCS = "gcs"


class OutputType(StrEnum):
    HTTP_ENDPOINT = "http_endpoint"
    GRPC_ENDPOINT = "grpc_endpoint"
    TOPIC = "topic"
    QUEUE = "queue"
    DATASET = "dataset"
    TABLE = "table"
    COLLECTION = "collection"
    CONNECTION_STRING = "connection_string"
    SELF_LINK = "self_link"
    IP_ADDRESS = "ip_address"
    BUCKET = "bucket"


COMPUTE_TYPES: set[NodeType] = {
    NodeType.CLOUD_RUN,
    NodeType.CLOUD_RUN_JOB,
    NodeType.CLOUD_FUNCTION,
}

# Types that can carry an internalGraph (behavioral steps).
# All compute types own their workflow definition directly.
GRAPH_TYPES: set[NodeType] = {NodeType.CLOUD_RUN, NodeType.CLOUD_RUN_JOB, NodeType.CLOUD_FUNCTION}

# §3 action validation table
ACTION_VALID_TARGETS: dict[ActionType, set[NodeType]] = {
    ActionType.READ: {
        NodeType.CLOUD_SQL, NodeType.FIRESTORE, NodeType.BIGQUERY,
        NodeType.BIGTABLE, NodeType.GCS_BUCKET,
    },
    ActionType.WRITE: {
        NodeType.CLOUD_SQL, NodeType.FIRESTORE, NodeType.BIGQUERY,
        NodeType.BIGTABLE, NodeType.GCS_BUCKET,
    },
    ActionType.INVOKE: {
        NodeType.CLOUD_RUN, NodeType.CLOUD_FUNCTION, NodeType.THIRD_PARTY_API,
    },
    ActionType.EMIT: {NodeType.PUBSUB_TOPIC},
    ActionType.ENQUEUE: {NodeType.CLOUD_TASK_QUEUE},
}

# Child node types that are embedded in parent TF templates (empty -- all child types
# now have their own config models and are handled by attach_child_resources).
CHILD_DATA_TYPES: set[NodeType] = set()

# Maps child node type to its expected parent node type.
CHILD_PARENT_MAP: dict[NodeType, NodeType] = {
    NodeType.FIRESTORE_COLLECTION: NodeType.FIRESTORE,
    NodeType.BIGQUERY_TABLE: NodeType.BIGQUERY,
    NodeType.CLOUD_SQL_DATABASE: NodeType.CLOUD_SQL,
    NodeType.CLOUD_SQL_TABLE: NodeType.CLOUD_SQL_DATABASE,
}
