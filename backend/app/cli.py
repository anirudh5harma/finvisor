from __future__ import annotations

import argparse
import json

from .agents.financial_advisor import ChatAgent
from .api.dependencies import get_loader
from .core.config import get_settings
from .core.logging import configure_logging


def main() -> None:
    configure_logging(get_settings().log_level)
    parser = argparse.ArgumentParser(description="Run the financial advisor chat agent.")
    parser.add_argument("--question", required=True)
    parser.add_argument("--portfolio", dest="portfolio_id")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    response = ChatAgent(get_loader()).answer(args.question, args.portfolio_id)
    if args.json:
        print(response.model_dump_json(indent=2))
    else:
        print(response.answer)
        print(f"\nConfidence: {response.confidence_score}")
        print(f"Evaluation score: {response.evaluation.score}")
        print(f"Evidence: {json.dumps(response.evidence, indent=2)}")


if __name__ == "__main__":
    main()
