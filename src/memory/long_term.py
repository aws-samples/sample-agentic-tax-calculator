"""Long-term memory using AgentCore Memory with semantic retrieval.

Stores user preferences and calculation summaries across sessions.
Uses ``semanticMemoryStrategy`` and ``summaryMemoryStrategy`` for
automatic extraction.  PII is filtered before storage via the
guardrails PII filter.

Requirements: 19.2, 19.3, 19.4, 19.5, 19.6
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from src.config.settings import AppSettings
from src.guardrails.pii_filter import PIIFilter

logger = logging.getLogger(__name__)


@dataclass
class UserPreferences:
    """Persisted user preferences for returning-user pre-population."""

    default_jurisdiction: str = ""
    preferred_accounting_method: str = ""
    default_business_id: str = ""
    last_tax_year: int = 0


@dataclass
class CalcSummary:
    """PII-filtered calculation summary stored in long-term memory."""

    workflow_id: str = ""
    jurisdiction: str = ""
    tax_year: int = 0
    total_tax: float = 0.0
    calculated_at: str = ""


class LongTermMemory:
    """Cross-session user preferences and calculation history.

    Uses ``bedrock-agentcore-control`` for ``CreateMemory`` and
    ``bedrock-agentcore`` for ``CreateEvent`` (ingestion) and
    ``RetrieveMemoryRecords`` (semantic search of extracted memories).

    PII is stripped via ``PIIFilter.filter_for_memory()`` before any
    data is persisted.
    """

    def __init__(
        self,
        memory_id: Optional[str] = None,
        settings: Optional[AppSettings] = None,
    ) -> None:
        self._settings = settings or AppSettings()
        self._memory_id = memory_id or "tax-calc-long-term"
        self._pii_filter = PIIFilter()

        self._control_client = boto3.client(
            "bedrock-agentcore-control",
            region_name=self._settings.aws_region,
        )
        self._runtime_client = boto3.client(
            "bedrock-agentcore",
            region_name=self._settings.aws_region,
        )

    # -- Memory namespace creation -------------------------------------------

    def ensure_memory_exists(self) -> None:
        """Create the long-term memory namespace if it doesn't exist."""
        try:
            self._control_client.create_memory(
                memoryId=self._memory_id,
                memoryStrategies=[
                    {
                        "semanticMemoryStrategy": {
                            "name": "user-preferences",
                            "description": (
                                "Extracts user tax preferences such as "
                                "default jurisdiction and accounting method"
                            ),
                            "namespace": "preferences",
                        }
                    },
                    {
                        "summaryMemoryStrategy": {
                            "name": "calculation-summaries",
                            "description": (
                                "Summarises completed tax calculations "
                                "for returning-user context"
                            ),
                            "namespace": "summaries",
                        }
                    },
                ],
            )
            logger.info("Created long-term memory: %s", self._memory_id)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code in ("ConflictException", "ResourceAlreadyExistsException"):
                logger.debug("Long-term memory already exists: %s", self._memory_id)
            else:
                logger.error("Failed to create long-term memory: %s", exc)
                raise

    # -- Preferences ---------------------------------------------------------

    def store_preferences(self, user_id: str, prefs: UserPreferences) -> None:
        """Store user preferences after PII filtering."""
        raw = json.dumps(asdict(prefs))
        filtered = self._pii_filter.filter_for_memory(raw)

        if filtered.blocked:
            logger.warning("Preferences blocked by PII filter user=%s", user_id)
            return

        try:
            self._runtime_client.create_event(
                memoryId=self._memory_id,
                sessionId=f"prefs-{user_id}",
                actorId=user_id,
                eventPayload={
                    "content": [
                        {"text": f"User {user_id} preferences: {filtered.text}"}
                    ]
                },
            )
            logger.info("Stored preferences for user=%s", user_id)
        except ClientError as exc:
            logger.error("Failed to store preferences user=%s: %s", user_id, exc)
            raise

    def get_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """Retrieve preferences via semantic search."""
        try:
            resp = self._runtime_client.retrieve_memory_records(
                memoryId=self._memory_id,
                namespace="preferences",
                query=f"preferences for user {user_id}",
                maxRecords=1,
            )

            records = resp.get("memoryRecords", [])
            if not records:
                return None

            content = records[0].get("content", "")
            try:
                idx = content.index("{")
                data = json.loads(content[idx:])
                return UserPreferences(**data)
            except (ValueError, json.JSONDecodeError):
                logger.warning("Could not parse preferences user=%s", user_id)
                return None

        except ClientError as exc:
            logger.error("Failed to get preferences user=%s: %s", user_id, exc)
            return None

    # -- Calculation summaries -----------------------------------------------

    def store_calculation_summary(
        self, user_id: str, summary: CalcSummary
    ) -> None:
        """Store a PII-filtered calculation summary."""
        raw = json.dumps(asdict(summary))
        filtered = self._pii_filter.filter_for_memory(raw)

        if filtered.blocked:
            logger.warning("Calc summary blocked by PII filter user=%s", user_id)
            return

        try:
            self._runtime_client.create_event(
                memoryId=self._memory_id,
                sessionId=f"calcs-{user_id}",
                actorId=user_id,
                eventPayload={
                    "content": [
                        {
                            "text": (
                                f"Tax calculation for user {user_id}: "
                                f"{filtered.text}"
                            )
                        }
                    ]
                },
            )
            logger.info(
                "Stored calc summary user=%s workflow=%s",
                user_id,
                summary.workflow_id,
            )
        except ClientError as exc:
            logger.error("Failed to store calc summary user=%s: %s", user_id, exc)
            raise

    def get_calculation_history(
        self, user_id: str, max_records: int = 10
    ) -> list[CalcSummary]:
        """Retrieve past calculation summaries via semantic search."""
        try:
            resp = self._runtime_client.retrieve_memory_records(
                memoryId=self._memory_id,
                namespace="summaries",
                query=f"tax calculations for user {user_id}",
                maxRecords=max_records,
            )

            results: list[CalcSummary] = []
            for record in resp.get("memoryRecords", []):
                content = record.get("content", "")
                try:
                    idx = content.index("{")
                    data = json.loads(content[idx:])
                    results.append(CalcSummary(**data))
                except (ValueError, json.JSONDecodeError):
                    continue
            return results

        except ClientError as exc:
            logger.error("Failed to get calc history user=%s: %s", user_id, exc)
            return []
