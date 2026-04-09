"""Tests for Block 9 — topic hints detection (app/domain/topic_hints.py)."""

from app.domain.topic_hints import TopicHint, detect_topic_hint

# ── 9.1: clickable-scenario detection ──────────────────────────────


class TestScenarioDetection:
    """detect_topic_hint must return the correct scenario_id."""

    def test_hire_keywords(self):
        assert detect_topic_hint("Как оформить приём сотрудника?").scenario_id == "hire"
        assert detect_topic_hint("Нужен трудовой договор").scenario_id == "hire"

    def test_fire_keywords(self):
        assert detect_topic_hint("Процедура увольнения").scenario_id == "fire"
        assert detect_topic_hint("Хочу уволиться").scenario_id == "fire"

    def test_vacation_keywords(self):
        assert detect_topic_hint("Как оформить отпуск?").scenario_id == "vacation"
        assert detect_topic_hint("График отпусков на следующий год").scenario_id == "vacation"

    def test_pay_keywords(self):
        assert detect_topic_hint("Условия премирования").scenario_id == "pay"
        assert detect_topic_hint("Оплата сверхурочных").scenario_id == "pay"

    def test_sick_keywords(self):
        assert detect_topic_hint("Как оформить больничный?").scenario_id == "sick"
        assert detect_topic_hint("Электронный листок нетрудоспособности").scenario_id == "sick"

    def test_probation_keywords(self):
        assert detect_topic_hint("Испытательный срок").scenario_id == "probation"

    def test_no_match_returns_none(self):
        result = detect_topic_hint("Где найти кулер с водой?")
        assert result.scenario_id is None

    def test_case_insensitive(self):
        assert detect_topic_hint("УВОЛЬНЕНИЕ").scenario_id == "fire"
        assert detect_topic_hint("Отпуск").scenario_id == "vacation"


# ── 9.2: background-topic disclaimers ──────────────────────────────


class TestBackgroundTopicDisclaimers:
    """detect_topic_hint must attach a disclaimer for background topics."""

    def test_transfer_disclaimer(self):
        hint = detect_topic_hint("Как оформить перевод сотрудника?")
        assert hint.disclaimer is not None
        assert "HR" in hint.disclaimer

    def test_discipline_disclaimer(self):
        hint = detect_topic_hint("Порядок дисциплинарного взыскания")
        assert hint.disclaimer is not None
        assert "HR" in hint.disclaimer

    def test_absenteeism_disclaimer(self):
        hint = detect_topic_hint("Увольнение за прогул")
        assert hint.disclaimer is not None
        assert "HR" in hint.disclaimer

    def test_regular_topic_no_disclaimer(self):
        hint = detect_topic_hint("Как оформить отпуск?")
        assert hint.disclaimer is None

    def test_unknown_topic_no_disclaimer(self):
        hint = detect_topic_hint("Где найти кулер с водой?")
        assert hint.disclaimer is None


# ── combined: scenario + disclaimer ────────────────────────────────


class TestCombinedHint:
    """A question can match both a scenario and a disclaimer."""

    def test_absenteeism_has_fire_scenario_and_disclaimer(self):
        hint = detect_topic_hint("Увольнение за прогул")
        assert hint.scenario_id == "fire"
        assert hint.disclaimer is not None

    def test_default_is_no_match(self):
        hint = detect_topic_hint("")
        assert hint == TopicHint()


# ── 9.1: ask handler uses qa_service (not rag_stub) ──────────────


class TestAskHandlerImports:
    """Verify the ask handler now imports qa_service instead of rag_stub."""

    def test_ask_handler_imports_qa_service(self):
        from app.integrations.vk.handlers import ask

        assert hasattr(ask, "get_qa_service")

    def test_ask_handler_does_not_import_rag_stub(self):
        import inspect

        import app.integrations.vk.handlers.ask as ask_mod

        source = inspect.getsource(ask_mod)
        assert "rag_stub" not in source

    def test_ask_handler_imports_topic_hints(self):
        from app.integrations.vk.handlers import ask

        assert hasattr(ask, "detect_topic_hint")
