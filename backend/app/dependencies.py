from __future__ import annotations

from functools import lru_cache

from .chat_agent import ChatAgent
from .config import get_settings
from .data_loader import DataLoader


@lru_cache(maxsize=1)
def get_loader() -> DataLoader:
    return DataLoader(get_settings().data_dir)


@lru_cache(maxsize=1)
def get_chat_agent() -> ChatAgent:
    return ChatAgent(get_loader(), settings=get_settings())

