# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""Agent factories. Always CALL these at composition time (never reuse an agent
instance across two parents — ADK enforces a single parent)."""

from .aeo import create_aeo_specialist
from .collectors import (
    create_backlink,
    create_competitor_discovery,
    create_keyword_research,
    create_serp_aeo,
    create_technical_audit,
)
from .execution import (
    create_implementation,
    create_improvement_reporter,
    create_monitoring,
    create_scorer,
    create_verifier,
)
from .strategy import (
    create_action_plan,
    create_content_optimizer,
    create_critic,
    create_strategy_synthesizer,
)

__all__ = [
    "create_action_plan",
    "create_aeo_specialist",
    "create_backlink",
    "create_competitor_discovery",
    "create_content_optimizer",
    "create_critic",
    "create_implementation",
    "create_improvement_reporter",
    "create_keyword_research",
    "create_monitoring",
    "create_scorer",
    "create_serp_aeo",
    "create_strategy_synthesizer",
    "create_technical_audit",
    "create_verifier",
]
