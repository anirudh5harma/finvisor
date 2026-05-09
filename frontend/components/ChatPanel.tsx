"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

import { sendChat, type ChatResponse } from "@/lib/api";

type Message = {
  role: "user" | "agent";
  content: string;
};

type Props = {
  portfolioId: string;
  onResponse: (response: ChatResponse) => void;
  onLoadingChange: (isLoading: boolean) => void;
};

const EXAMPLES = [
  "Why did my portfolio fall today?",
  "What are the biggest risks in this portfolio?",
  "Explain today's market sentiment.",
];

export function ChatPanel({ portfolioId, onResponse, onLoadingChange }: Props) {
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "agent",
      content: `Context loaded for ${portfolioId}. Ask a portfolio, market, stock, or mutual fund question.`
    }
  ]);
  const [input, setInput] = useState(EXAMPLES[0]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ block: "end", behavior: "smooth" });
  }, [messages, isLoading]);

  async function submit(event?: FormEvent<HTMLFormElement>, override?: string) {
    event?.preventDefault();
    const message = (override ?? input).trim();
    if (!message || isLoading) return;

    setMessages((current) => [...current, { role: "user", content: message }]);
    setInput("");
    setError(null);
    setIsLoading(true);
    onLoadingChange(true);

    try {
      const response = await sendChat(message, portfolioId);
      onResponse(response);
      setMessages((current) => [...current, { role: "agent", content: response.answer }]);
    } catch (caught) {
      const nextError = caught instanceof Error ? caught.message : "Unable to reach backend.";
      setError(nextError);
    } finally {
      setIsLoading(false);
      onLoadingChange(false);
    }
  }

  return (
    <section className="panel chat-panel">
      <div className="eyebrow">Advisor Chat</div>
      <div className="examples">
        {EXAMPLES.map((example) => (
          <button type="button" key={example} disabled={isLoading} onClick={() => void submit(undefined, example)}>
            {example}
          </button>
        ))}
      </div>
      <div className="messages">
        {messages.map((message, index) => (
          <div className={`message ${message.role}`} key={`${message.role}-${index}`}>
            {message.content.split("\n").map((line, lineIndex) => (
              <p key={`${message.role}-${index}-${lineIndex}`}>{line}</p>
            ))}
          </div>
        ))}
        {isLoading && (
          <div className="message agent loading-card" aria-live="polite">
            <span className="thinking-loader" aria-hidden="true" />
            <div>
              <strong>Analyzing portfolio impact</strong>
              <p>Checking market, news, holdings, and risk signals.</p>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      {error && <p className="error">{error}</p>}
      <form onSubmit={(event) => void submit(event)}>
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Ask about your portfolio..."
        />
        <button type="submit" disabled={isLoading}>
          {isLoading ? <span className="loader" aria-label="Loading" /> : "Send"}
        </button>
      </form>
    </section>
  );
}
