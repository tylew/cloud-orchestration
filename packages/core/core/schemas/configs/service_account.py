from pydantic import BaseModel, field_validator
import re


class IamRole(BaseModel):
    role: str  # e.g. roles/cloudsql.client
    resource: str = ""  # blank = project-level, otherwise resource node name
    description: str = ""


class ServiceAccountConfig(BaseModel):
    account_id: str = ""
    display_name: str = ""
    description: str = ""
    disabled: bool = False
    roles: list[IamRole] = []

    @field_validator("account_id")
    @classmethod
    def validate_account_id(cls, v: str) -> str:
        if not v:
            return v
        if len(v) > 30:
            raise ValueError("account_id must be at most 30 characters")
        if not re.match(r"^[a-z][a-z0-9-]*$", v):
            raise ValueError("account_id must match ^[a-z][a-z0-9-]*$")
        return v
