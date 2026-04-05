"""Legal entity definitions used across hire, vacation, and HR-request flows."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LegalEntity:
    id: int
    short_name: str
    full_name: str


# NFR-7: buttons must show full legal-entity names.
ENTITIES: tuple[LegalEntity, ...] = (
    LegalEntity(1, "Кофейни Кафетера", 'ООО «Кофейни Кафетера»'),
    LegalEntity(2, "Кафетера Рус", 'ООО «Кафетера Рус»'),
    LegalEntity(3, "ИП Кафетера", "ИП Кафетера"),
    LegalEntity(4, "Кафетера Групп", 'ООО «Кафетера Групп»'),
)

ENTITY_BY_ID: dict[int, LegalEntity] = {e.id: e for e in ENTITIES}
