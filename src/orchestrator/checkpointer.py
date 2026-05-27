"""Checkpointer factory for the LangGraph workflow.

Wraps LangGraph's DynamoDB checkpointer for production use and falls
back to an in-memory checkpointer for local development.

Requirements: 6.4
"""

from __future__ import annotations

import logging
from typing import Optional

from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)


def create_checkpointer(
    table_name: Optional[str] = None,
    region: Optional[str] = None,
    use_memory: bool = False,
):
    """Create a LangGraph-compatible checkpointer.

    Args:
        table_name: DynamoDB table name.  Defaults to AppSettings value.
        region: AWS region.  Defaults to AppSettings value.
        use_memory: Force in-memory checkpointer (local dev / testing).

    Returns:
        A LangGraph BaseCheckpointSaver instance.
    """
    if use_memory:
        logger.info("Using in-memory checkpointer (local dev mode)")
        return MemorySaver()

    # Resolve defaults from config when not explicitly provided
    if table_name is None or region is None:
        from src.config.settings import AppSettings

        settings = AppSettings()
        table_name = table_name or settings.dynamodb_table_name
        region = region or settings.aws_region

    try:
        from langgraph.checkpoint.aws import DynamoDBSaver

        logger.info(
            "Using DynamoDB checkpointer (table=%s, region=%s)",
            table_name,
            region,
        )
        return DynamoDBSaver.from_conn_info(
            table_name=table_name,
            region_name=region,
        )
    except Exception as exc:
        logger.warning(
            "DynamoDB checkpointer unavailable (%s); falling back to "
            "in-memory checkpointer",
            exc,
        )
        return MemorySaver()
