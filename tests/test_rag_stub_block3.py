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


class TestFireRagUsesQaService:
    """3.2 — fire handler uses send_rag_answer helper for RAG (Block 7+8)."""

    def test_fire_handler_imports_send_rag_answer(self):
        from app.integrations.vk.handlers import fire

        assert hasattr(fire, "send_rag_answer")

    def test_fire_module_has_no_section_stub(self):
        import app.integrations.vk.handlers.fire as fire_mod

        assert not hasattr(fire_mod, "_SECTION_STUB")


class TestVacationRagUsesQaService:
    """3.3 — vacation handler uses send_rag_answer helper for RAG (Block 7+8)."""

    def test_vacation_handler_imports_send_rag_answer(self):
        from app.integrations.vk.handlers import vacation

        assert hasattr(vacation, "send_rag_answer")

    def test_vacation_module_has_no_rag_stub_const(self):
        import app.integrations.vk.handlers.vacation as vac_mod

        assert not hasattr(vac_mod, "_RAG_STUB")


class TestPaySectionUsesQaService:
    """3.4 — pay section uses send_rag_answer helper for RAG (Block 7+8)."""

    def test_pay_handler_imports_send_rag_answer(self):
        from app.integrations.vk.handlers import pay

        assert hasattr(pay, "send_rag_answer")


class TestSectionsUsesQaService:
    """Block 8 — sections handler uses qa_service for RAG."""

    def test_sections_handler_imports_qa_service(self):
        from app.integrations.vk.handlers import sections

        assert hasattr(sections, "get_qa_service")


# ── Block 5/8 — handlers now RAG-powered ──────────────────────────


class TestVacationScheduleHandler:
    """5.1/8.1 — vacation schedule navigator handler exists (FR-11)."""

    def test_rag_stub_function_still_works(self):
        result = rag_stub("Навигатор по графику отпусков")
        assert "Навигатор по графику отпусков" in result

    def test_vacation_handler_has_schedule_handler(self):
        from app.integrations.vk.handlers import vacation

        assert hasattr(vacation, "on_vacation_schedule")


class TestFireGroundsHandler:
    """5.3/8.3 — dismissal grounds handler exists (FR-12)."""

    def test_rag_stub_function_still_works(self):
        result = rag_stub("Основания увольнения")
        assert "Основания увольнения" in result

    def test_fire_handler_has_grounds_handler(self):
        from app.integrations.vk.handlers import fire

        assert hasattr(fire, "on_fire_grounds")
