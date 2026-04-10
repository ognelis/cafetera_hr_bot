"""Category file models for VK bot document templates."""

from __future__ import annotations

import dataclasses
import datetime


@dataclasses.dataclass
class CategoryFileRecord:
    file_id: str                # UUID hex
    category: str               # e.g. "hire"
    subcategory: str            # e.g. "hire_checklist"
    entity_id: int              # 1-4
    filename: str               # original filename
    s3_key: str                 # S3 object path
    mime_type: str
    size_bytes: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
    id: int | None = None       # auto-generated DB row ID


# Legal entities (mirrors keyboards.py entity_select_kb)
LEGAL_ENTITIES: dict[int, str] = {
    1: "ООО «Кафетера Групп Рус»",
    2: "ООО «Вкусно»",
    3: "ООО «Аврора РусКо»",
    4: "ООО «СМАРТ ПИТАНИЕ»",
}

# Valid category → subcategory slots with Russian labels
CATEGORY_SLOTS: dict[str, dict] = {
    "hire": {
        "label": "Приём сотрудника",
        "subcategories": {
            "hire_checklist": "Чек-лист документов",
            "hire_contract": "Шаблон трудового договора",
            "hire_onboarding": "Онбординг-чек-лист",
        },
    },
    "fire": {
        "label": "Увольнение",
        "subcategories": {
            "fire_checklist": "Чек-лист последнего дня",
            "fire_bypass": "Обходной лист",
            "fire_resignation": "Заявление об увольнении по собственному",
        },
    },
    "vacation": {
        "label": "Отпуск",
        "subcategories": {
            "vacation_paid": "Заявление на оплачиваемый отпуск",
            "vacation_unpaid": "Заявление за свой счёт",
        },
    },
}


def is_valid_slot(category: str, subcategory: str) -> bool:
    """Check if a category+subcategory combination is valid."""
    cat = CATEGORY_SLOTS.get(category)
    if cat is None:
        return False
    return subcategory in cat["subcategories"]
