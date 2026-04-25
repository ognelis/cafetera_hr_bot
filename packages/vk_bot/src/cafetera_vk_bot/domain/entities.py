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
    LegalEntity(1, "Кафетера", 'ООО «Кафетера Групп Рус»'),
    LegalEntity(2, "Вкусно", 'ООО «Вкусно»'),
    LegalEntity(3, "Аврора", 'ООО «Аврора РусКо»'),
    LegalEntity(4, "СМАРТ", 'ООО «СМАРТ ПИТАНИЕ»'),
)

ENTITY_BY_ID: dict[int, LegalEntity] = {e.id: e for e in ENTITIES}