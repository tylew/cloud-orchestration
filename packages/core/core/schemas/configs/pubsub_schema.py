from pydantic import BaseModel


class PubsubSchemaConfig(BaseModel):
    type: str = "AVRO"
    definition: str = ""
