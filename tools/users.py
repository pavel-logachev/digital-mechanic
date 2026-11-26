"""Управление учетными записями: python -m tools.users add ivanov "Иванов И. И." mechanic
                               python -m tools.users list | disable ivanov | password ivanov
Пароль вводится с клавиатуры и хранится только хешем. После первой записи сервис требует вход."""
from __future__ import annotations

import getpass
import json
import sys

from app import config, users


def main(argv: list[str]) -> None:
    rows = json.loads(config.USERS_FILE.read_text(encoding="utf-8")) if config.USERS_FILE.exists() else []
    cmd = argv[0] if argv else "list"
    if cmd == "list":
        for r in rows:
            print(r["login"], r.get("name", ""), users.ROLES.get(r["role"], r["role"]), "отключен" if r.get("disabled") else "")
        return
    login = argv[1].lower()
    row = next((r for r in rows if r["login"] == login), None)
    if cmd == "add":
        if row:
            sys.exit("Такой логин уже есть")
        role = argv[3] if len(argv) > 3 else "mechanic"
        if role not in users.ROLES:
            sys.exit("Роль: mechanic или chief")
        rows.append({"login": login, "name": argv[2], "role": role, "password": users.hash_password(_ask())})
    elif cmd == "password" and row:
        row["password"] = users.hash_password(_ask())
    elif cmd == "disable" and row:
        row["disabled"] = True
    else:
        sys.exit("Нет такого пользователя или команды")
    users.save(rows)
    print("Готово:", config.USERS_FILE)


def _ask() -> str:
    first = getpass.getpass("Пароль (не короче 8 символов): ")
    if len(first) < 8 or first != getpass.getpass("Повторите: "):
        sys.exit("Пароли не совпадают или слишком короткие")
    return first


if __name__ == "__main__":
    main(sys.argv[1:])
