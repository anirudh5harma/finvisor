from __future__ import annotations

import json
from functools import cached_property
from pathlib import Path
from typing import Any


class DataLoader:
    """Loads the supplied financial datasets from disk."""

    def __init__(self, data_dir: Path | str | None = None) -> None:
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).resolve().parents[3]

    def _load_json(self, filename: str) -> dict[str, Any]:
        path = self.data_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Dataset not found: {path}")
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    @cached_property
    def market_data(self) -> dict[str, Any]:
        return self._load_json("market_data.json")

    @cached_property
    def news_data(self) -> dict[str, Any]:
        return self._load_json("news_data.json")

    @cached_property
    def portfolios_data(self) -> dict[str, Any]:
        return self._load_json("portfolios.json")

    @cached_property
    def mutual_funds_data(self) -> dict[str, Any]:
        return self._load_json("mutual_funds.json")

    @cached_property
    def historical_data(self) -> dict[str, Any]:
        return self._load_json("historical_data.json")

    @cached_property
    def sector_mapping(self) -> dict[str, Any]:
        return self._load_json("sector_mapping.json")

    def list_portfolios(self) -> list[dict[str, Any]]:
        portfolios = self.portfolios_data.get("portfolios", {})
        return [
            {
                "portfolio_id": portfolio_id,
                "user_name": portfolio.get("user_name"),
                "portfolio_type": portfolio.get("portfolio_type"),
                "risk_profile": portfolio.get("risk_profile"),
                "current_value": portfolio.get("current_value"),
                "day_change_percent": portfolio.get("analytics", {})
                .get("day_summary", {})
                .get("day_change_percent"),
            }
            for portfolio_id, portfolio in portfolios.items()
        ]

    def get_portfolio(self, portfolio_id: str) -> dict[str, Any]:
        portfolios = self.portfolios_data.get("portfolios", {})
        if portfolio_id not in portfolios:
            raise KeyError(f"Unknown portfolio_id: {portfolio_id}")
        return portfolios[portfolio_id]

    def get_stock(self, symbol: str) -> dict[str, Any] | None:
        return self.market_data.get("stocks", {}).get(symbol.upper())

    def get_mutual_fund(self, scheme_code: str) -> dict[str, Any] | None:
        return self.mutual_funds_data.get("mutual_funds", {}).get(scheme_code.upper())

    def find_stock_symbol(self, text: str) -> str | None:
        normalized = text.upper()
        for symbol, stock in self.market_data.get("stocks", {}).items():
            if symbol in normalized or stock.get("name", "").upper() in normalized:
                return symbol
        return None

    def find_mutual_fund_code(self, text: str) -> str | None:
        normalized = text.upper()
        normalized_lower = text.lower()
        for scheme_code, fund in self.mutual_funds_data.get("mutual_funds", {}).items():
            scheme_name = fund.get("scheme_name", "")
            if scheme_code in normalized or scheme_name.lower() in normalized_lower:
                return scheme_code
        return None
