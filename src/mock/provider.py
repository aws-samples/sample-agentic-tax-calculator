"""Mock data provider that loads JSON files and serves data keyed by business_id."""

import json
import os
from typing import Any, Optional


class MockDataProvider:
    """Provides mock data from JSON files, mirroring the GraphQL API response format.

    Data is loaded lazily from src/mock/data/ and keyed by business_id.
    """

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), "data")
        self._data_dir = data_dir
        self._cache: dict[str, Any] = {}

    def _load(self, filename: str) -> dict:
        """Load and cache a JSON data file."""
        if filename not in self._cache:
            path = os.path.join(self._data_dir, filename)
            with open(path, "r") as f:
                self._cache[filename] = json.load(f)
        return self._cache[filename]

    def get_business_info(self, business_id: str, tax_year: int) -> dict:
        """Return business metadata for a given business_id.

        Raises KeyError if business_id is not found.
        """
        data = self._load("business.json")
        if business_id not in data:
            raise KeyError(f"Unknown business_id: {business_id}")
        return data[business_id]

    def get_income(self, business_id: str, tax_year: int) -> dict:
        """Return income (CREDIT accounts) for a given business_id.

        Raises KeyError if business_id is not found.
        """
        data = self._load("income.json")
        if business_id not in data:
            raise KeyError(f"Unknown business_id: {business_id}")
        return data[business_id]

    def get_expenses(self, business_id: str, tax_year: int) -> dict:
        """Return expenses (DEBIT accounts) for a given business_id.

        Raises KeyError if business_id is not found.
        """
        data = self._load("expenses.json")
        if business_id not in data:
            raise KeyError(f"Unknown business_id: {business_id}")
        return data[business_id]

    def get_assets(self, business_id: str, tax_year: int) -> dict:
        """Return HST/GST tax account data for a given business_id.

        Raises KeyError if business_id is not found.
        """
        data = self._load("assets.json")
        if business_id not in data:
            raise KeyError(f"Unknown business_id: {business_id}")
        return data[business_id]

    def get_tax_rules(self, jurisdiction: str, tax_year: int) -> dict:
        """Return tax rules for a given jurisdiction.

        Returns federal rules plus the matching provincial rules.
        Returns None if the jurisdiction is not found in provincial data.
        """
        data = self._load("tax_rules.json")
        result: dict[str, Any] = {
            "federal": data.get("federal"),
            "cpp": data.get("cpp"),
            "ei": data.get("ei"),
        }
        provincial = data.get("provincial", {})
        if jurisdiction in provincial:
            result["provincial"] = provincial[jurisdiction]
        else:
            return None  # type: ignore[return-value]
        return result
