import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ContextSection:
    """A section of context with priority and token count."""

    name: str
    content: str
    priority: int
    token_count: int = 0

    def __post_init__(self):
        if self.token_count == 0 and self.content:
            self.token_count = estimate_tokens(self.content)


@dataclass
class ContextBuilder:
    """
    Build LLM context with priority-based truncation and
    "Lost in the Middle" mitigation.

    Priority levels (0-100):
    - 100: Task description (always included)
    - 90: Output format specification
    - 80: System prompt / agent role
    - 70: Self-awareness prompt (model strengths/limitations)
    - 60: Validation gate results
    - 50: Relevant memory / past lessons
    - 40: Related module specs
    - 30: Architectural laws
    - 20: Full codebase context
    - 10: Historical audit logs

    "Lost in the Middle" mitigation:
    - Critical info placed at BEGINNING and END of context
    - Less critical info placed in MIDDLE
    - Based on research: LLMs pay most attention to start/end of context
    """

    max_tokens: int = 128000
    safety_margin: int = 4096
    sections: list[ContextSection] = field(default_factory=list)

    def add_section(self, name: str, content: str, priority: int) -> None:
        """Add a context section with given priority."""
        if not content:
            return
        section = ContextSection(name=name, content=content, priority=priority)
        self.sections.append(section)

    def build(self) -> str:
        """
        Build final context string with priority truncation and
        "Lost in the Middle" mitigation.

        Strategy:
        1. Sort sections by priority (highest first)
        2. Truncate lowest priority sections until within token limit
        3. Reorder: critical sections at start AND end, less critical in middle
        """
        if not self.sections:
            return ""

        available_tokens = self.max_tokens - self.safety_margin

        sections_by_priority = sorted(self.sections, key=lambda s: s.priority, reverse=True)

        included_sections: list[ContextSection] = []
        total_tokens = 0

        for section in sections_by_priority:
            if total_tokens + section.token_count <= available_tokens:
                included_sections.append(section)
                total_tokens += section.token_count
            else:
                remaining = available_tokens - total_tokens
                if remaining > 100:
                    truncated = truncate_content(section.content, remaining)
                    truncated_section = ContextSection(
                        name=section.name,
                        content=truncated,
                        priority=section.priority,
                        token_count=remaining,
                    )
                    included_sections.append(truncated_section)
                    total_tokens += remaining
                break

        reordered = self._reorder_for_attention(included_sections)

        context_parts = []
        for section in reordered:
            context_parts.append(f"## {section.name}\n\n{section.content}\n")

        final_context = "\n".join(context_parts)
        final_token_count = estimate_tokens(final_context)

        if final_token_count > self.max_tokens:
            logger.warning(
                f"Context still exceeds limit after truncation: "
                f"{final_token_count} > {self.max_tokens}"
            )

        logger.info(
            f"Context built: {len(included_sections)} sections, "
            f"{final_token_count} tokens (limit: {self.max_tokens})"
        )

        return final_context

    def _reorder_for_attention(
        self, sections: list[ContextSection]
    ) -> list[ContextSection]:
        """
        Reorder sections to mitigate "Lost in the Middle" phenomenon.

        Research shows LLMs pay most attention to:
        - First ~20% of context
        - Last ~20% of context
        - Least attention to middle ~60%

        Strategy:
        - Highest priority (>= 80): BEGINNING
        - Medium priority (40-79): MIDDLE
        - Lower priority (20-39): END (but still visible)
        - Lowest priority (< 20): END (least important)
        """
        beginning = [s for s in sections if s.priority >= 80]
        middle = [s for s in sections if 40 <= s.priority < 80]
        end = [s for s in sections if s.priority < 40]

        beginning.sort(key=lambda s: s.priority, reverse=True)
        middle.sort(key=lambda s: s.priority, reverse=True)
        end.sort(key=lambda s: s.priority, reverse=True)

        return beginning + middle + end

    def get_summary(self) -> dict[str, Any]:
        """Get summary of context composition."""
        total_tokens = sum(s.token_count for s in self.sections)
        return {
            "total_sections": len(self.sections),
            "total_tokens": total_tokens,
            "max_tokens": self.max_tokens,
            "utilization": round(total_tokens / self.max_tokens * 100, 1),
            "sections": [
                {
                    "name": s.name,
                    "priority": s.priority,
                    "tokens": s.token_count,
                }
                for s in sorted(self.sections, key=lambda s: s.priority, reverse=True)
            ],
        }


def estimate_tokens(text: str) -> int:
    """
    Rough token estimation: ~4 chars per token for English text.
    For accurate counting, use tiktoken or provider-specific tokenizer.
    """
    if not text:
        return 0
    return max(1, len(text) // 4)


def truncate_content(content: str, max_tokens: int) -> str:
    """Truncate content to fit within token limit, preserving beginning and end."""
    if estimate_tokens(content) <= max_tokens:
        return content

    max_chars = max_tokens * 4

    if len(content) <= max_chars:
        return content

    half = max_chars // 2
    return content[:half] + "\n...[truncated]...\n" + content[-half:]
