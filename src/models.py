from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class Article:
    id: str
    title: str
    description: str
    url: str
    published_at: str
    source: str
    raw: Dict[str, Any]
