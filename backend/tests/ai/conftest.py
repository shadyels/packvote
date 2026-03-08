import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "live: marks tests as requiring real API credentials (use '-m not live' to skip)",
    )
