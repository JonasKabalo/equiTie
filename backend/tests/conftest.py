from __future__ import annotations

import pytest

from app.data import DataStore, get_store


@pytest.fixture(scope="session")
def store() -> DataStore:
    return get_store()
