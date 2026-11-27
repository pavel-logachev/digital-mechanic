"""Тесты работают на собственном синтетическом парке (tests/fixtures), а не на данных заказчика.

Данные заглушек заказчика по требованию организаторов в Git не хранятся (см. README, «Материалы задачи»).
Пути задаются до импорта app.config, поэтому переменные окружения переопределяются здесь, в самом начале.
"""
import os
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"
os.environ["VEHICLES_PATH"] = str(FIXTURES / "fleet.json")
os.environ["FAULT_TYPES_PATH"] = str(FIXTURES / "fault_types.json")
