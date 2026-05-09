"use client";

import type { PortfolioSummary } from "@/lib/api";

type Props = {
  portfolios: PortfolioSummary[];
  selectedId: string;
  onSelect: (portfolioId: string) => void;
};

export function PortfolioSelector({ portfolios, selectedId, onSelect }: Props) {
  return (
    <section className="panel">
      <div className="eyebrow">Portfolio Context</div>
      <select
        value={selectedId}
        onChange={(event) => onSelect(event.target.value)}
        aria-label="Select portfolio"
      >
        {portfolios.map((portfolio) => (
          <option key={portfolio.portfolio_id} value={portfolio.portfolio_id}>
            {portfolio.user_name} · {portfolio.portfolio_type}
          </option>
        ))}
      </select>
      <div className="portfolio-grid">
        {portfolios.map((portfolio) => (
          <button
            type="button"
            className={portfolio.portfolio_id === selectedId ? "portfolio-card active" : "portfolio-card"}
            key={portfolio.portfolio_id}
            onClick={() => onSelect(portfolio.portfolio_id)}
          >
            <span>{portfolio.user_name}</span>
            <strong>{portfolio.day_change_percent}%</strong>
            <small>{portfolio.risk_profile}</small>
          </button>
        ))}
      </div>
    </section>
  );
}
