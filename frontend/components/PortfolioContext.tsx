"use client";

import type { PortfolioDetail } from "@/lib/api";

type Props = {
  portfolio?: PortfolioDetail;
  isLoading: boolean;
};

export function PortfolioContext({ portfolio, isLoading }: Props) {
  return (
    <section className="panel context-panel">
      <div className="eyebrow">Selected Context</div>
      {isLoading && <p className="muted">Loading portfolio context...</p>}
      {!isLoading && !portfolio && <p className="muted">Select a portfolio to load analytics.</p>}
      {portfolio && (
        <div className="context-grid">
          <div>
            <span>Person</span>
            <strong>{portfolio.user_name}</strong>
          </div>
          <div>
            <span>Day P&L</span>
            <strong>{portfolio.day_change_percent}%</strong>
          </div>
          <div>
            <span>Largest Sector</span>
            <strong>{portfolio.risk_metrics.largest_sector ?? "N/A"}</strong>
          </div>
          <div>
            <span>Concentration</span>
            <strong>{portfolio.risk_metrics.concentration_risk ? "Risk" : "OK"}</strong>
          </div>
        </div>
      )}
    </section>
  );
}
