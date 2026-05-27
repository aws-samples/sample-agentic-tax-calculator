"""PII pre-filter guardrail for agent inputs and memory storage.

Detects and redacts personally identifiable information before data
reaches the LLM or is persisted to long-term memory.  Implements the
AgentCore Gateway REQUEST interceptor pattern - executes before the
gateway forwards the request to the target agent/tool.

Supported PII types:
  - Canadian Social Insurance Numbers (SIN): XXX-XXX-XXX
  - Bank account numbers (5-12 digit sequences in financial context)
  - Person names (common Canadian first/last name heuristic)
  - Street addresses (Canadian postal-code anchored)

Requirements: 13.1, 13.2, 13.3
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class PIIFilterResult:
    """Outcome of a PII filtering pass."""

    text: str
    redacted: bool = False
    blocked: bool = False
    redaction_count: int = 0
    redacted_types: list[str] = field(default_factory=list)


# -- PII regex patterns -----------------------------------------------------

_SIN_PATTERN = re.compile(r"\b\d{3}[-\s]\d{3}[-\s]\d{3}\b")

_BANK_CONTEXT_KEYWORDS = re.compile(
    r"(?:account|routing|transit|bank|acct)[\s]*(?:number|num|no|#)?[:\s#]*(\d{5,12})\b",
    re.IGNORECASE,
)
_BANK_STANDALONE = re.compile(r"\b\d{7,12}\b")

_POSTAL_CODE = re.compile(r"\b[A-Za-z]\d[A-Za-z][\s-]?\d[A-Za-z]\d\b")

_ADDRESS_PATTERN = re.compile(
    r"\b\d{1,5}\s+[\w\s]{2,30}"
    r"(?:street|st|avenue|ave|road|rd|drive|dr"
    r"|boulevard|blvd|lane|ln|crescent|cres|court|ct|way|place|pl)\b",
    re.IGNORECASE,
)

_NAME_CONTEXT = re.compile(
    r"(?:name|client|customer|taxpayer|owner|contact)"
    r"[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
)

# -- Redaction placeholders --------------------------------------------------

_REDACTION_MAP: dict[str, str] = {
    "SIN": "[REDACTED-SIN]",
    "BANK_ACCOUNT": "[REDACTED-BANK-ACCT]",
    "ADDRESS": "[REDACTED-ADDRESS]",
    "POSTAL_CODE": "[REDACTED-POSTAL]",
    "NAME": "[REDACTED-NAME]",
}


class PIIFilter:
    """Pre-filter that detects and redacts PII from text.

    Modelled after the AgentCore Gateway interceptor pattern:
    a REQUEST interceptor that validates/transforms the payload
    before the gateway forwards it to the target runtime.
    """

    def filter_input(self, text: str) -> PIIFilterResult:
        """Detect and redact PII from agent input text.

        If PII is found but cannot be safely redacted (the entire
        payload is PII), the result is ``blocked=True`` and the
        original text is *not* returned.
        """
        if not text or not text.strip():
            return PIIFilterResult(text=text)

        filtered = text
        count = 0
        types_found: list[str] = []

        # SIN
        sins = _SIN_PATTERN.findall(filtered)
        if sins:
            filtered = _SIN_PATTERN.sub(_REDACTION_MAP["SIN"], filtered)
            count += len(sins)
            types_found.append("SIN")

        # Bank account (contextual)
        bank_ctx = _BANK_CONTEXT_KEYWORDS.findall(filtered)
        if bank_ctx:
            filtered = _BANK_CONTEXT_KEYWORDS.sub(
                lambda m: m.group(0).replace(
                    m.group(1), _REDACTION_MAP["BANK_ACCOUNT"]
                ),
                filtered,
            )
            count += len(bank_ctx)
            types_found.append("BANK_ACCOUNT")

        # Street address
        addrs = _ADDRESS_PATTERN.findall(filtered)
        if addrs:
            filtered = _ADDRESS_PATTERN.sub(_REDACTION_MAP["ADDRESS"], filtered)
            count += len(addrs)
            types_found.append("ADDRESS")

        # Postal code (standalone)
        postals = _POSTAL_CODE.findall(filtered)
        if postals:
            filtered = _POSTAL_CODE.sub(_REDACTION_MAP["POSTAL_CODE"], filtered)
            count += len(postals)
            if "ADDRESS" not in types_found:
                types_found.append("ADDRESS")

        # Names (context-anchored)
        names = _NAME_CONTEXT.findall(filtered)
        if names:
            filtered = _NAME_CONTEXT.sub(
                lambda m: m.group(0).replace(
                    m.group(1), _REDACTION_MAP["NAME"]
                ),
                filtered,
            )
            count += len(names)
            types_found.append("NAME")

        redacted = count > 0
        blocked = self._should_block(filtered, count)

        if blocked:
            return PIIFilterResult(
                text="",
                redacted=True,
                blocked=True,
                redaction_count=count,
                redacted_types=types_found,
            )

        return PIIFilterResult(
            text=filtered,
            redacted=redacted,
            blocked=False,
            redaction_count=count,
            redacted_types=types_found,
        )

    def filter_for_memory(self, text: str) -> PIIFilterResult:
        """Strip PII before storing in long-term memory.

        Same detection as ``filter_input`` plus an aggressive pass that
        redacts standalone long digit sequences (potential account
        numbers) even without financial-context keywords.

        Requirements: 19.4, 19.5
        """
        result = self.filter_input(text)
        if result.blocked:
            return result

        extra = _BANK_STANDALONE.findall(result.text)
        if extra:
            result.text = _BANK_STANDALONE.sub(
                _REDACTION_MAP["BANK_ACCOUNT"], result.text
            )
            result.redaction_count += len(extra)
            result.redacted = True
            if "BANK_ACCOUNT" not in result.redacted_types:
                result.redacted_types.append("BANK_ACCOUNT")

        return result

    # -- internal helpers ----------------------------------------------------

    @staticmethod
    def _should_block(filtered: str, redaction_count: int) -> bool:
        """Block when the non-redacted content is too small to be useful."""
        if redaction_count == 0:
            return False
        remaining = filtered
        for placeholder in _REDACTION_MAP.values():
            remaining = remaining.replace(placeholder, "")
        remaining = remaining.strip()
        return len(remaining) < 10
