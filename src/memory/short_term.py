"""Short-term memory using AgentCore Memory CreateEvent / ListEvents.

Session-scoped storage for intermediate agent results and conversation
context during a single tax calculation workflow.  Events are stored
via the AgentCore Memory ``CreateEvent`` API and retrieved with
``ListEvents``, both keyed by ``sessionId``.

Requirements: 19.1
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError

from src.config.settings import AppSettings

logger = logging.getLogger(__name__)


class ShortTermMemory:
    """Session-scoped memory backed by AgentCore Memory events.

    Uses the ``bedrock-agentcore`` runtime client:
    - ``CreateEvent`` to store key/value pairs as session events
    - ``ListEvents`` to retrieve all events for a session
    """

    def __init__(
        self,
        memory_id: Optional[str] = None,
        settings: Optional[AppSettings] = None,
    ) -> None:
        self._settings = settings or AppSettings()
        self._memory_id = memory_id or "tax-calc-short-term"
        self._client = boto3.client(
            "bedrock-agentcore",
            region_name=self._settings.aws_region,
        )

    def store(self, session_id: str, key: str, value: Any) -> None:
        """Store a key/value pair as a session event."""
        payload = json.dumps(
            {
                "key": key,
                "value": value,
                "stored_at": datetime.now(timezone.utc).isoformat(),
            }
        )

        try:
            self._client.create_event(
                memoryId=self._memory_id,
                sessionId=session_id,
                actorId="agentic-tax-calculator",
                eventPayload={"content": [{"text": payload}]},
            )
            logger.debug(
                "Stored short-term event session=%s key=%s", session_id, key
            )
        except ClientError as exc:
            logger.error(
                "Failed to store short-term event session=%s key=%s: %s",
                session_id,
                key,
                exc,
            )
            raise

    def retrieve(self, session_id: str, key: str) -> Optional[Any]:
        """Retrieve the most recent value for *key* in *session_id*."""
        try:
            response = self._client.list_events(
                memoryId=self._memory_id,
                sessionId=session_id,
            )

            events = response.get("events", [])
            for event in reversed(events):
                payload_content = (
                    event.get("eventPayload", {}).get("content", [{}])
                )
                for item in payload_content:
                    text = item.get("text", "")
                    try:
                        data = json.loads(text)
                        if data.get("key") == key:
                            return data.get("value")
                    except (json.JSONDecodeError, TypeError):
                        continue

            return None

        except ClientError as exc:
            logger.error(
                "Failed to retrieve short-term event session=%s key=%s: %s",
                session_id,
                key,
                exc,
            )
            return None

    def retrieve_all(self, session_id: str) -> dict[str, Any]:
        """Retrieve all key/value pairs for *session_id*."""
        result: dict[str, Any] = {}

        try:
            response = self._client.list_events(
                memoryId=self._memory_id,
                sessionId=session_id,
            )

            for event in response.get("events", []):
                payload_content = (
                    event.get("eventPayload", {}).get("content", [{}])
                )
                for item in payload_content:
                    text = item.get("text", "")
                    try:
                        data = json.loads(text)
                        k = data.get("key")
                        if k:
                            result[k] = data.get("value")
                    except (json.JSONDecodeError, TypeError):
                        continue

        except ClientError as exc:
            logger.error(
                "Failed to list short-term events session=%s: %s",
                session_id,
                exc,
            )

        return result

    def clear_session(self, session_id: str) -> None:
        """Clear all events for *session_id*.

        AgentCore Memory does not expose a bulk-delete API, so we
        store a sentinel event that downstream consumers interpret as
        a session reset.
        """
        self.store(session_id, "__session_cleared__", True)
        logger.info("Cleared short-term memory for session=%s", session_id)
