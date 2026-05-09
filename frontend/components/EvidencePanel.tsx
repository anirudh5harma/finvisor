"use client";

import type { ChatResponse } from "@/lib/api";

type Props = {
  response?: ChatResponse;
  isLoading: boolean;
};

export function EvidencePanel({ response, isLoading }: Props) {
  const conflicts = response?.reasoning_chains.filter((chain) => chain.conflict).length ?? 0;

  return (
    <aside className="panel evidence-panel">
      <div className="eyebrow">Evidence</div>
      {isLoading ? (
        <p className="muted">Waiting for reasoning output...</p>
      ) : !response ? (
        <p className="muted">Ask a question to see confidence, evaluation, and source signals.</p>
      ) : (
        <>
          <div className="score-row">
            <span>Confidence</span>
            <strong>{Math.round(response.confidence_score * 100)}%</strong>
          </div>
          <div className="score-row">
            <span>Evaluation</span>
            <strong>{response.evaluation.score}/100</strong>
          </div>
          <div className="score-row"><span>Causal Chains</span><strong>{response.reasoning_chains.length}</strong></div>
          <div className="score-row"><span>Conflicts</span><strong>{conflicts}</strong></div>
          {response.response_metadata.fallback_reason && (
            <p className="warning">{response.response_metadata.fallback_reason}</p>
          )}
          <h3>Sectors</h3>
          <p className="muted">{response.evidence.sectors.slice(0, 5).join(", ") || "None"}</p>
          <h3>News Evidence</h3>
          <div className="news-list">
            {response.evidence.news.slice(0, 3).map((news) => (
              <article key={news.id}>
                <span>{news.id} · {news.impact_level} · {news.sentiment}</span>
                <p>{news.headline}</p>
              </article>
            ))}
          </div>
          {response.evaluation.missing_elements.length > 0 && (
            <>
              <h3>Evaluation Gaps</h3>
              {response.evaluation.missing_elements.map((item) => (
                <p className="warning" key={item}>{item}</p>
              ))}
            </>
          )}
        </>
      )}
    </aside>
  );
}
