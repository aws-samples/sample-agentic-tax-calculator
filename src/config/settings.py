"""
Pydantic-settings based configuration for the Agentic Tax Calculator.

All external dependencies are exposed as environment variables with the
TAX_CALC_ prefix. The system works out of the box with mock data - no
external credentials required.
"""

from enum import Enum

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings


class DeploymentMode(str, Enum):
    """Target deployment platform."""

    AGENTCORE = "agentcore"
    KUBERNETES = "kubernetes"


class MCPDeploymentMode(str, Enum):
    """How MCP tool groups are deployed."""

    CONSOLIDATED = "consolidated"
    SEPARATE = "separate"


class DataSourceMode(str, Enum):
    """Where business data comes from."""

    MOCK = "mock"
    GRAPHQL = "graphql"


class AuthMode(str, Enum):
    """Authentication strategy.

    passthrough: Accept bearer token from request, forward to GraphQL.
                 No validation on agent side - GraphQL handles it.
    okta:        Okta OAuth 2.0 via AgentCore Identity (client-credentials).
    auth0:       Auth0 OAuth 2.0 (future - planned).
    agentcore_identity: AgentCore Identity with registered IDP.
    """

    PASSTHROUGH = "passthrough"
    OKTA = "okta"
    AUTH0 = "auth0"
    AGENTCORE_IDENTITY = "agentcore_identity"


class MemoryBackend(str, Enum):
    """Where workflow state and long-term memory are stored.

    dynamodb:  Self-managed DynamoDB tables. Cheapest option.
    agentcore: AgentCore Memory (managed, built-in strategies). ~300x more
               expensive than DynamoDB at scale but zero custom code.
    """

    DYNAMODB = "dynamodb"
    AGENTCORE = "agentcore"


class AppSettings(BaseSettings):
    """Central configuration for the Agentic Tax Calculator.

    Every field maps to a TAX_CALC_<FIELD> environment variable.
    Defaults are tuned for local/mock operation so the starter kit
    works immediately after deployment.
    """

    # --- Deployment ---------------------------------------------------------
    deployment_mode: DeploymentMode = DeploymentMode.AGENTCORE
    mcp_deployment_mode: MCPDeploymentMode = MCPDeploymentMode.CONSOLIDATED

    # --- Data source --------------------------------------------------------
    data_source_mode: DataSourceMode = DataSourceMode.MOCK
    graphql_endpoint: str = ""

    # --- Auth ---------------------------------------------------------------
    auth_mode: AuthMode = AuthMode.PASSTHROUGH
    # Okta/Auth0 fields - optional, only required when auth_mode is okta/auth0
    okta_domain: str = ""
    okta_client_id: str = ""
    okta_client_secret: str = ""

    # --- Gateway (disabled by default - enable for multi-MCP or Cedar) ------
    gateway_enabled: bool = False
    gateway_url: str = ""

    # --- Memory backend -----------------------------------------------------
    memory_backend: MemoryBackend = MemoryBackend.DYNAMODB

    # --- DynamoDB -----------------------------------------------------------
    dynamodb_table_name: str = "tax-calc-shared-state"
    memory_table_name: str = "tax-calc-memory"

    # --- Memory -------------------------------------------------------------
    memory_retention_days: int = 90

    # --- LLM ----------------------------------------------------------------
    llm_model_id: str = "anthropic.claude-sonnet-4-6-20250514"

    # --- AWS ----------------------------------------------------------------
    aws_region: str = "us-east-1"

    # --- Observability ------------------------------------------------------
    datadog_api_key: str = ""
    streamlit_metrics_port: int = 8501
    log_level: str = "INFO"

    # ---- Validators --------------------------------------------------------

    @field_validator("graphql_endpoint")
    @classmethod
    def _graphql_endpoint_format(cls, v: str) -> str:
        if v and not v.startswith(("http://", "https://")):
            raise ValueError(
                f"graphql_endpoint must be a valid HTTP(S) URL, got: '{v}'"
            )
        return v

    @field_validator("memory_retention_days")
    @classmethod
    def _memory_retention_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError(
                f"memory_retention_days must be >= 1, got: {v}"
            )
        return v

    @field_validator("streamlit_metrics_port")
    @classmethod
    def _valid_port(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError(
                f"streamlit_metrics_port must be between 1 and 65535, got: {v}"
            )
        return v

    @field_validator("log_level")
    @classmethod
    def _valid_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(
                f"log_level must be one of {sorted(allowed)}, got: '{v}'"
            )
        return upper

    @model_validator(mode="after")
    def _graphql_mode_requires_endpoint(self) -> "AppSettings":
        if self.data_source_mode == DataSourceMode.GRAPHQL and not self.graphql_endpoint:
            raise ValueError(
                "graphql_endpoint is required when data_source_mode is 'graphql'. "
                "Set TAX_CALC_GRAPHQL_ENDPOINT to the GraphQL API URL."
            )
        return self

    model_config = {
        "env_prefix": "TAX_CALC_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }
