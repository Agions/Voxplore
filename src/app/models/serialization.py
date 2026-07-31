"""Dataclass serialization helpers used by lightweight models."""

from __future__ import annotations

from dataclasses import asdict, fields
from typing import Any, TypeVar

T = TypeVar("T", bound="SerializableDataclass")


class SerializableDataclass:
    """Small mixin for dataclasses that serialize to plain dictionaries."""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls: type[T], data: dict[str, Any]) -> T:
        field_names = {field.name for field in fields(cls)}
        return cls(**{key: value for key, value in data.items() if key in field_names})
