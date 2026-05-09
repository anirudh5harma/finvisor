"use client";

import { useEffect, useState } from "react";

import { ChatPanel } from "@/components/ChatPanel";
import { EvidencePanel } from "@/components/EvidencePanel";
import { PortfolioContext } from "@/components/PortfolioContext";
import { PortfolioSelector } from "@/components/PortfolioSelector";
import { fetchPortfolio, fetchPortfolios, type ChatResponse, type PortfolioDetail, type PortfolioSummary } from "@/lib/api";

export default function Home() {
  const [portfolios, setPortfolios] = useState<PortfolioSummary[]>([]);
  const [selectedPortfolioId, setSelectedPortfolioId] = useState("");
  const [selectedPortfolio, setSelectedPortfolio] = useState<PortfolioDetail>();
  const [isPortfolioLoading, setIsPortfolioLoading] = useState(false);
  const [response, setResponse] = useState<ChatResponse>();
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    fetchPortfolios()
      .then((items) => {
        if (!isActive) return;
        setPortfolios(items);
        setSelectedPortfolioId(items[1]?.portfolio_id ?? items[0]?.portfolio_id ?? "");
      })
      .catch((caught) => {
        if (!isActive) return;
        setError(caught instanceof Error ? caught.message : "Unable to load portfolios.");
      });

    return () => {
      isActive = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedPortfolioId) return;
    let isActive = true;
    setIsPortfolioLoading(true);

    fetchPortfolio(selectedPortfolioId)
      .then((portfolio) => {
        if (!isActive) return;
        setSelectedPortfolio(portfolio);
      })
      .catch((caught) => {
        if (!isActive) return;
        setError(caught instanceof Error ? caught.message : "Unable to load portfolio context.");
      })
      .finally(() => {
        if (isActive) setIsPortfolioLoading(false);
      });

    return () => {
      isActive = false;
    };
  }, [selectedPortfolioId]);

  return (
    <main>
      <section className="hero">
        <div>
          <div className="eyebrow">Finvisor</div>
          <p>Links market news, sector trends, and stock holdings to portfolio impact.</p>
        </div>
      </section>

      {error && <p className="error">{error}</p>}

      <div className="layout">
        <div className="left-column">
          <PortfolioSelector
            portfolios={portfolios}
            selectedId={selectedPortfolioId}
            onSelect={(portfolioId) => {
              setSelectedPortfolioId(portfolioId);
              setResponse(undefined);
              setIsChatLoading(false);
            }}
          />
          <PortfolioContext portfolio={selectedPortfolio} isLoading={isPortfolioLoading} />
          <EvidencePanel response={response} isLoading={isChatLoading} />
        </div>
        {selectedPortfolioId && (
          <ChatPanel
            key={selectedPortfolioId}
            portfolioId={selectedPortfolioId}
            onResponse={setResponse}
            onLoadingChange={(loading) => {
              setIsChatLoading(loading);
              if (loading) setResponse(undefined);
            }}
          />
        )}
      </div>
    </main>
  );
}
