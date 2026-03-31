from pydantic import BaseModel


class IamRole(BaseModel):
    role: str  # e.g. roles/cloudsql.client
    resource: str = ""  # blank = project-level, otherwise resource node name
    description: str = ""


class ServiceAccountConfig(BaseModel):
    display_name: str = ""
    description: str = ""
    disabled: bool = False
    roles: list[IamRole] = []
