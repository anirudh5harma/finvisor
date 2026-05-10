from backend.app.agents.financial_advisor import ChatAgent
from backend.app.data.loader import DataLoader
from backend.app.services.market_intelligence import MarketIntelligence
from backend.app.services.portfolio_analytics import PortfolioAnalytics


def test_portfolio_002_concentration_and_loss():
    loader = DataLoader()
    analysis = PortfolioAnalytics(loader.mutual_funds_data).analyze(
        "PORTFOLIO_002",
        loader.get_portfolio("PORTFOLIO_002"),
    )

    assert analysis["day_change_percent"] == -2.73
    assert analysis["risk_metrics"]["concentration_risk"] is True
    assert analysis["risk_metrics"]["largest_sector"] == "BANKING"


def test_market_summary_is_bearish():
    loader = DataLoader()
    summary = MarketIntelligence(
        loader.market_data,
        loader.news_data,
        loader.historical_data,
        loader.sector_mapping,
    ).market_summary()

    assert summary["sentiment"] == "BEARISH"


def test_chat_agent_identifies_banking_driver():
    response = ChatAgent(DataLoader()).answer(
        "Why did my portfolio fall today?",
        "PORTFOLIO_002",
    )

    assert response.confidence_score > 0.6
    assert "NEWS001" in response.evidence["news_ids"]
    assert "BANKING" in response.evidence["sectors"]
    assert response.evaluation.score >= 70


def test_chat_agent_varies_answers_by_question_intent():
    agent = ChatAgent(DataLoader())

    impact = agent.answer("Why did my portfolio fall today?", "PORTFOLIO_002")
    risk = agent.answer("What are the biggest risks in this portfolio?", "PORTFOLIO_002")
    market = agent.answer("Explain today's market sentiment.", "PORTFOLIO_002")

    assert impact.answer != risk.answer
    assert risk.answer != market.answer
    assert "Largest sector exposure" in risk.answer
    assert "Market sentiment" in market.answer


def test_chat_agent_surfaces_conflict_question():
    response = ChatAgent(DataLoader()).answer(
        "Which holdings had conflicting signals?",
        "PORTFOLIO_002",
    )

    assert "Conflicting signals" in response.answer
    assert any(chain.get("conflict") for chain in response.reasoning_chains)


def test_chat_agent_handles_stock_and_fund_questions():
    agent = ChatAgent(DataLoader())

    stock = agent.answer("Tell me about INFY stock")
    fund = agent.answer("Analyze MF005 mutual fund")

    assert stock.response_metadata["intent"] == "stock_analysis"
    assert "INFY" in stock.answer
    assert fund.response_metadata["intent"] == "mutual_fund_analysis"
    assert "MF005" in fund.answer
    assert stock.response_metadata["token_usage"]["total_tokens"] > 0


def test_chat_agent_handles_general_finance_question_without_symbol():
    response = ChatAgent(DataLoader()).answer("What is a mutual fund?")

    assert response.response_metadata["intent"] == "general_finance"
    assert "pools money" in response.answer


def test_chat_agent_general_finance_definition_does_not_include_market_insights():
    response = ChatAgent(DataLoader()).answer("What is finance in general?", "PORTFOLIO_002")

    assert response.response_metadata["intent"] == "general_finance"
    assert response.response_metadata["provider"] == "deterministic"
    assert "management of money" in response.answer
    assert response.reasoning_chains == []
    assert response.evidence["news_ids"] == []
    assert "market backdrop" not in response.answer.lower()
    assert "current driver" not in response.answer.lower()


def test_educational_market_question_is_not_dataset_market_summary():
    response = ChatAgent(DataLoader()).answer("What is the investment market?")

    assert response.response_metadata["intent"] == "general_finance"
    assert response.reasoning_chains == []
    assert response.evidence["news_ids"] == []


def test_current_market_question_still_uses_dataset_summary():
    response = ChatAgent(DataLoader()).answer("Explain today's market sentiment.")

    assert response.response_metadata["intent"] == "market_summary"
    assert response.evidence["news_ids"]
