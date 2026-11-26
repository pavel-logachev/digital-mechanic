"""Выгружает спецификации OpenAPI обеих заглушек в корень проекта.

    python tools/export_openapi.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from mock_ml.app import app as ml_app  # noqa: E402
from mock_toir.app import app as toir_app  # noqa: E402

for name, app in (("openapi_ml.json", ml_app), ("openapi_toir.json", toir_app)):
    with open(os.path.join(ROOT, name), "w", encoding="utf-8", newline="\n") as f:
        json.dump(app.openapi(), f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    print("written", name)
