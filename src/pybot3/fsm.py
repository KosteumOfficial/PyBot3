from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FSMContext:
    state: str = "idle"
    data: dict[str, Any] = field(default_factory=dict)


class FSM:
    def __init__(self, storage: dict[str, FSMContext] | None = None):
        self.storage = storage if storage is not None else {}

    def get(self, user_id: str | int) -> FSMContext:
        key = str(user_id)
        if key not in self.storage:
            self.storage[key] = FSMContext()
        return self.storage[key]

    def set_state(self, user_id: str | int, state: str) -> FSMContext:
        context = self.get(user_id)
        context.state = state
        return context

    def update_data(self, user_id: str | int, **kwargs: Any) -> FSMContext:
        context = self.get(user_id)
        context.data.update(kwargs)
        return context

    def clear(self, user_id: str | int) -> None:
        self.storage.pop(str(user_id), None)

    def reset(self, user_id: str | int) -> FSMContext:
        context = self.get(user_id)
        context.state = "idle"
        context.data.clear()
        return context


__all__ = ["FSM", "FSMContext"]
