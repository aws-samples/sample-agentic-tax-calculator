"""
Sensible default configuration values for mock / local development mode.

Use `get_mock_defaults()` to get a dict suitable for constructing
`AppSettings` when running without any environment variables set.
"""

from src.config.settings import (
    AppSettings,
    DataSourceMode,
    DeploymentMode,
    MCPDeploymentMode,
)

# Canonical defaults for running the starter kit in mock mode.
MOCK_DEFAULTS: dict = {
    "deployment_mode": DeploymentMode.AGENTCORE,
    "mcp_deployment_mode": MCPDeploymentMode.CONSOLIDATED,
    "data_source_mode": DataSourceMode.MOCK,
    "graphql_endpoint": "",
    "okta_domain": "",
    "okta_client_id": "",
    "okta_client_secret": "",
    "dynamodb_table_name": "tax-calc-shared-state",
    "memory_table_name": "tax-calc-memory",
    "memory_retention_days": 90,
    "llm_model_id": "anthropic.claude-sonnet-4-6-20250514",
    "aws_region": "us-east-1",
    "datadog_api_key": "",
    "streamlit_metrics_port": 8501,
    "log_level": "INFO",
}


def get_mock_defaults() -> dict:
    """Return a copy of the mock-mode default values."""
    return dict(MOCK_DEFAULTS)


def create_mock_settings() -> AppSettings:
    """Create an AppSettings instance pre-configured for mock mode.

    Useful in tests and local development where no env vars are set.
    """
    return AppSettings(**MOCK_DEFAULTS)
