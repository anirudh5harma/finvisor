from __future__ import annotations

from typing import Any

from ..core.config import Settings, get_settings


class PortfolioAnalytics:
    def __init__(self, mutual_funds: dict[str, Any], settings: Settings | None = None) -> None:
        self.mutual_funds = mutual_funds.get("mutual_funds", {})
        self.settings = settings or get_settings()

    def analyze(self, portfolio_id: str, portfolio: dict[str, Any]) -> dict[str, Any]:
        stocks = portfolio.get("holdings", {}).get("stocks", [])
        funds = portfolio.get("holdings", {}).get("mutual_funds", [])
        current_value = portfolio.get("current_value", 0.0)

        stock_impacts = [self._holding_impact(holding, current_value, "stock") for holding in stocks]
        fund_impacts = [self._holding_impact(holding, current_value, "mutual_fund") for holding in funds]
        all_impacts = sorted(stock_impacts + fund_impacts, key=lambda item: item["day_change"])

        sector_allocation = portfolio.get("analytics", {}).get("sector_allocation", {})
        indirect_fund_exposure = self._indirect_fund_exposure(funds)
        largest_sector, largest_sector_weight = self._largest_allocation(sector_allocation)
        concentration_risk = largest_sector_weight > self.settings.concentration_threshold_percent

        return {
            "portfolio_id": portfolio_id,
            "user_name": portfolio.get("user_name"),
            "portfolio_type": portfolio.get("portfolio_type"),
            "risk_profile": portfolio.get("risk_profile"),
            "investment_horizon": portfolio.get("investment_horizon"),
            "current_value": current_value,
            "overall_gain_loss": portfolio.get("overall_gain_loss"),
            "overall_gain_loss_percent": portfolio.get("overall_gain_loss_percent"),
            "day_change_absolute": round(sum(item["day_change"] for item in stock_impacts + fund_impacts), 2),
            "day_change_percent": portfolio.get("analytics", {}).get("day_summary", {}).get("day_change_percent"),
            "sector_allocation": sector_allocation,
            "asset_type_allocation": portfolio.get("analytics", {}).get("asset_type_allocation", {}),
            "indirect_fund_exposure": indirect_fund_exposure,
            "risk_metrics": {
                **portfolio.get("analytics", {}).get("risk_metrics", {}),
                "concentration_risk": concentration_risk,
                "largest_sector": largest_sector,
                "largest_sector_weight": largest_sector_weight,
            },
            "holding_impacts": all_impacts,
            "top_detractors": all_impacts[:5],
            "top_gainers": sorted(stock_impacts + fund_impacts, key=lambda item: item["day_change"], reverse=True)[:5],
            "symbols": sorted(
                {holding.get("symbol") for holding in stocks if holding.get("symbol")}
                | set(indirect_fund_exposure["symbols"])
            ),
            "sectors": sorted(
                {holding.get("sector") for holding in stocks if holding.get("sector")}
                | set(indirect_fund_exposure["sectors"])
            ),
        }

    def _holding_impact(self, holding: dict[str, Any], portfolio_value: float, asset_type: str) -> dict[str, Any]:
        identifier = holding.get("symbol") or holding.get("scheme_code")
        name = holding.get("name") or holding.get("scheme_name")
        value = holding.get("current_value", 0.0)
        day_change = holding.get("day_change", 0.0)
        day_change_percent = holding.get("day_change_percent", 0.0)
        portfolio_impact_percent = (day_change / portfolio_value * 100) if portfolio_value else 0.0

        return {
            "id": identifier,
            "name": name,
            "asset_type": asset_type,
            "sector": holding.get("sector") or holding.get("category"),
            "current_value": value,
            "weight_in_portfolio": holding.get("weight_in_portfolio", 0.0),
            "day_change": round(day_change, 2),
            "day_change_percent": day_change_percent,
            "portfolio_impact_percent": round(portfolio_impact_percent, 3),
            "top_holdings": self._fund_top_symbols(identifier, holding),
            "sector_exposure": self._fund_sector_exposure(identifier),
        }

    def _largest_allocation(self, allocation: dict[str, float]) -> tuple[str | None, float]:
        if not allocation:
            return None, 0.0
        sector, weight = max(allocation.items(), key=lambda item: item[1])
        return sector, float(weight)

    def _fund_top_symbols(self, identifier: str | None, holding: dict[str, Any]) -> list[str]:
        if not identifier or not identifier.startswith("MF"):
            return holding.get("top_holdings", [])

        fund = self.mutual_funds.get(identifier, {})
        raw_holdings = fund.get("top_holdings") or fund.get("top_equity_holdings") or []
        symbols = [
            item.get("stock")
            for item in raw_holdings
            if isinstance(item, dict) and item.get("stock")
        ]
        return symbols or holding.get("top_holdings", [])

    def _fund_sector_exposure(self, identifier: str | None) -> dict[str, float]:
        if not identifier or not identifier.startswith("MF"):
            return {}
        fund = self.mutual_funds.get(identifier, {})
        return fund.get("sector_allocation", {})

    def _indirect_fund_exposure(self, funds: list[dict[str, Any]]) -> dict[str, Any]:
        symbols: set[str] = set()
        sectors: set[str] = set()
        weighted_sector_exposure: dict[str, float] = {}

        for holding in funds:
            scheme_code = holding.get("scheme_code")
            fund = self.mutual_funds.get(scheme_code, {})
            portfolio_weight = float(holding.get("weight_in_portfolio", 0.0))
            raw_holdings = fund.get("top_holdings") or fund.get("top_equity_holdings") or []

            for item in raw_holdings:
                if not isinstance(item, dict):
                    continue
                if item.get("stock"):
                    symbols.add(item["stock"])
                if item.get("sector"):
                    sectors.add(item["sector"])

            for sector, fund_weight in fund.get("sector_allocation", {}).items():
                sectors.add(sector)
                weighted_sector_exposure[sector] = round(
                    weighted_sector_exposure.get(sector, 0.0) + portfolio_weight * float(fund_weight) / 100,
                    2,
                )

        return {
            "symbols": sorted(symbols),
            "sectors": sorted(sectors),
            "weighted_sector_exposure": dict(
                sorted(weighted_sector_exposure.items(), key=lambda item: item[1], reverse=True)
            ),
        }
