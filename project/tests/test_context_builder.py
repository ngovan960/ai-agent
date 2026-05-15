import pytest
from services.orchestrator.services.context_builder import (
    ContextBuilder,
    ContextSection,
    estimate_tokens,
    truncate_content,
)


class TestEstimateTokens:
    def test_empty_string(self):
        assert estimate_tokens("") == 0

    def test_short_string(self):
        assert estimate_tokens("hello") >= 1

    def test_approximate_ratio(self):
        text = "a" * 400
        tokens = estimate_tokens(text)
        assert tokens == 100

    def test_none_handling(self):
        assert estimate_tokens(None) == 0


class TestTruncateContent:
    def test_no_truncation_needed(self):
        content = "short content"
        result = truncate_content(content, max_tokens=100)
        assert result == content

    def test_truncation_preserves_beginning_and_end(self):
        content = "A" * 400 + "MIDDLE" + "B" * 400
        result = truncate_content(content, max_tokens=50)
        assert "A" in result
        assert "B" in result
        assert "[truncated]" in result


class TestContextSection:
    def test_auto_token_count(self):
        section = ContextSection(name="Test", content="hello world", priority=80)
        assert section.token_count > 0

    def test_manual_token_count(self):
        section = ContextSection(name="Test", content="hello", priority=80, token_count=10)
        assert section.token_count == 10


class TestContextBuilder:
    def test_empty_context(self):
        builder = ContextBuilder()
        assert builder.build() == ""

    def test_single_section(self):
        builder = ContextBuilder(max_tokens=10000, safety_margin=0)
        builder.add_section("Task", "Hello world", priority=100)
        context = builder.build()
        assert "Task" in context
        assert "Hello world" in context

    def test_priority_truncation(self):
        builder = ContextBuilder(max_tokens=30, safety_margin=0)
        builder.add_section("High", "A" * 100, priority=100)
        builder.add_section("Low", "B" * 100, priority=10)
        context = builder.build()
        assert "A" in context
        assert "B" not in context

    def test_reorder_for_attention(self):
        builder = ContextBuilder(max_tokens=10000, safety_margin=0)
        builder.add_section("Task", "task desc", priority=100)
        builder.add_section("Laws", "law content", priority=30)
        builder.add_section("Memory", "memory content", priority=50)
        context = builder.build()

        task_pos = context.find("Task")
        laws_pos = context.find("Laws")
        memory_pos = context.find("Memory")

        assert task_pos < memory_pos < laws_pos

    def test_get_summary(self):
        builder = ContextBuilder(max_tokens=10000, safety_margin=0)
        builder.add_section("Task", "task desc", priority=100)
        builder.add_section("Laws", "law content", priority=30)
        summary = builder.get_summary()
        assert summary["total_sections"] == 2
        assert summary["max_tokens"] == 10000
        assert len(summary["sections"]) == 2

    def test_safety_margin(self):
        builder = ContextBuilder(max_tokens=200, safety_margin=50)
        builder.add_section("Task", "A" * 100, priority=100)
        context = builder.build()
        tokens = estimate_tokens(context)
        assert tokens <= 150
