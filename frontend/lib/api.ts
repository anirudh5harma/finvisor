const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type PortfolioSummary = {
  portfolio_id: string;
  user_name: string;
  portfolio_type: string;
  risk_profile: string;
  current_value: number;
  day_change_percent: number;
};

export type PortfolioDetail = PortfolioSummary & {
  day_change_absolute: number;
  sector_allocation: Record<string, number>;
  asset_type_allocation: Record<string, number>;
  risk_metrics: {
    concentration_risk: boolean;
    largest_sector: string | null;
    largest_sector_weight: number;
    beta?: number;
    volatility?: string;
  };
};

export type ChatResponse = {
  answer: string;
  confidence_score: number;
  reasoning_chains: Array<Record<string, unknown>>;
  evidence: {
    news_ids: string[];
    symbols: string[];
    sectors: string[];
    news: Array<{
      id: string;
      headline: string;
      sentiment: string;
      impact_level: string;
      relevance_score: number | null;
    }>;
  };
  evaluation: {
    score: number;
    flags: string[];
    missing_elements: string[];
    criteria_scores: Record<string, number>;
  };
  response_metadata: {
    intent: string;
    provider: string;
    model: string;
    prompt_version: string;
    fallback_reason: string | null;
    token_usage: {
      prompt_tokens: number;
      completion_tokens: number;
      total_tokens: number;
    };
  };
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers
    }
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function fetchPortfolios() {
  return request<PortfolioSummary[]>("/api/portfolios");
}

export function fetchPortfolio(portfolioId: string) {
  return request<PortfolioDetail>(`/api/portfolios/${portfolioId}`);
}

export function sendChat(message: string, portfolioId?: string) {
  return request<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify({
      message,
      portfolio_id: portfolioId || null
    })
  });
}
