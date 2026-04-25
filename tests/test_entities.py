"""Tests for app.domain.entities — legal entity definitions."""

from cafetera_core.domain.entities import ENTITIES, ENTITY_BY_ID, LegalEntity


class TestEntities:
    def test_four_entities(self):
        assert len(ENTITIES) == 4

    def test_all_are_legal_entity(self):
        for e in ENTITIES:
            assert isinstance(e, LegalEntity)

    def test_ids_unique(self):
        ids = [e.id for e in ENTITIES]
        assert len(ids) == len(set(ids))

    def test_entity_by_id_lookup(self):
        for e in ENTITIES:
            assert ENTITY_BY_ID[e.id] is e

    def test_entity_has_full_name(self):
        for e in ENTITIES:
            assert len(e.full_name) > 0

    def test_entity_has_short_name(self):
        for e in ENTITIES:
            assert len(e.short_name) > 0
