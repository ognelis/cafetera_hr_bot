"""Tests for Block 3 — RAG stub service and handler wiring."""

from app.domain.content import rag_stub


class TestRagStub:
    """3.1 — rag_stub(topic) must return a standardised placeholder."""

    def test_contains_topic(self):
        result = rag_stub("Увольнение по собственному желанию")
        assert "Увольнение по собственному желанию" in result

    def test_contains_kb_marker(self):
        result = rag_stub("Порядок оформления отпуска")
        assert "базу знаний" in result

    def test_contains_hr_fallback(self):
        result = rag_stub("Условия премирования")
        assert "Обратитесь в HR" in result

    def test_contains_info_emoji(self):
        result = rag_stub("anything")
        assert result.startswith("ℹ️")

    def test_different_topics_produce_different_text(self):
        a = rag_stub("Тема A")
        b = rag_stub("Тема B")
        assert a != b
        assert "Тема A" in a
        assert "Тема B" in b


class TestFireRagUsesStub:
    """3.2 — fire handler must use rag_stub, not an inline string."""

    def test_fire_handler_imports_rag_stub(self):
        from app.integrations.vk.handlers import fire

        # The handler module must reference the shared rag_stub function
        assert hasattr(fire, "rag_stub") or "rag_stub" in dir(fire)

    def test_fire_module_has_no_section_stub(self):
        import app.integrations.vk.handlers.fire as fire_mod

        assert not hasattr(fire_mod, "_SECTION_STUB")


class TestVacationRagUsesStub:
    """3.3 — vacation handler must use rag_stub, not an inline string."""

    def test_vacation_handler_imports_rag_stub(self):
        from app.integrations.vk.handlers import vacation

        assert hasattr(vacation, "rag_stub") or "rag_stub" in dir(vacation)

    def test_vacation_module_has_no_rag_stub_const(self):
        import app.integrations.vk.handlers.vacation as vac_mod

        assert not hasattr(vac_mod, "_RAG_STUB")


class TestPaySectionUsesRagStub:
    """3.4 — pay section must use rag_stub for FR-10."""

    def test_sections_handler_imports_rag_stub(self):
        from app.integrations.vk.handlers import sections

        assert hasattr(sections, "rag_stub") or "rag_stub" in dir(sections)
