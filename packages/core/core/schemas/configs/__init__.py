"""Config model index — maps NodeType to its Pydantic config model."""

from pydantic import BaseModel

from core.schemas.enums import NodeType

from .service_account import ServiceAccountConfig
from .vpc import VpcConfig
from .subnet import SubnetConfig
from .vpc_connector import VpcConnectorConfig
from .gcs_bucket import GcsBucketConfig
from .cloud_sql import CloudSqlConfig, CloudSqlDatabaseConfig
from .firestore import FirestoreConfig
from .bigquery import BigQueryConfig, BigQueryTableConfig
from .bigtable import BigtableConfig
from .pubsub_schema import PubsubSchemaConfig
from .pubsub_topic import PubsubTopicConfig
from .pubsub_subscription import PubsubSubscriptionConfig
from .cloud_task_queue import CloudTaskQueueConfig
from .cloud_run import CloudRunConfig
from .cloud_run_job import CloudRunJobConfig
from .cloud_function import CloudFunctionConfig
from .external_lb import ExternalLbConfig
from .cloud_dns import CloudDnsConfig

TYPE_TO_CONFIG: dict[NodeType, type[BaseModel]] = {
    NodeType.SERVICE_ACCOUNT: ServiceAccountConfig,
    NodeType.VPC: VpcConfig,
    NodeType.SUBNET: SubnetConfig,
    NodeType.VPC_CONNECTOR: VpcConnectorConfig,
    NodeType.GCS_BUCKET: GcsBucketConfig,
    NodeType.CLOUD_SQL: CloudSqlConfig,
    NodeType.FIRESTORE: FirestoreConfig,
    NodeType.BIGQUERY: BigQueryConfig,
    NodeType.BIGTABLE: BigtableConfig,
    NodeType.PUBSUB_SCHEMA: PubsubSchemaConfig,
    NodeType.PUBSUB_TOPIC: PubsubTopicConfig,
    NodeType.PUBSUB_SUBSCRIPTION: PubsubSubscriptionConfig,
    NodeType.CLOUD_TASK_QUEUE: CloudTaskQueueConfig,
    NodeType.CLOUD_RUN: CloudRunConfig,
    NodeType.CLOUD_RUN_JOB: CloudRunJobConfig,
    NodeType.CLOUD_FUNCTION: CloudFunctionConfig,
    NodeType.EXTERNAL_LB: ExternalLbConfig,
    NodeType.CLOUD_DNS: CloudDnsConfig,
    NodeType.BIGQUERY_TABLE: BigQueryTableConfig,
    NodeType.CLOUD_SQL_DATABASE: CloudSqlDatabaseConfig,
}

NodeConfig = (
    ServiceAccountConfig | VpcConfig | SubnetConfig | VpcConnectorConfig
    | GcsBucketConfig | CloudSqlConfig | FirestoreConfig
    | BigQueryConfig | BigtableConfig | PubsubSchemaConfig | PubsubTopicConfig
    | PubsubSubscriptionConfig | CloudTaskQueueConfig | CloudRunConfig
    | CloudRunJobConfig | CloudFunctionConfig
    | ExternalLbConfig | CloudDnsConfig
    | BigQueryTableConfig | CloudSqlDatabaseConfig
)
