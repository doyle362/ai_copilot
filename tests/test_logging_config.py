import logging

import pytest

from analyst.logging_utils import JsonFormatter, configure_logging
from analyst.config import settings


@pytest.fixture(autouse=True)
def restore_logging():
    original_handlers = logging.getLogger().handlers[:]
    original_level = logging.getLogger().level
    original_json = settings.log_json
    original_level_setting = settings.log_level
    try:
        yield
    finally:
        # Restore logger handlers and level
        root = logging.getLogger()
        for handler in root.handlers[:]:
            root.removeHandler(handler)
        for handler in original_handlers:
            root.addHandler(handler)
        root.setLevel(original_level)
        settings.log_json = original_json
        settings.log_level = original_level_setting


def test_configure_logging_plain_text():
    settings.log_json = False
    settings.log_level = "DEBUG"

    configure_logging()

    root = logging.getLogger()
    assert root.level == logging.DEBUG
    assert len(root.handlers) == 1
    formatter = root.handlers[0].formatter
    assert isinstance(formatter, logging.Formatter)
    assert not isinstance(formatter, JsonFormatter)


def test_configure_logging_json():
    settings.log_json = True
    settings.log_level = "INFO"

    configure_logging()

    root = logging.getLogger()
    assert root.level == logging.INFO
    assert len(root.handlers) == 1
    formatter = root.handlers[0].formatter
    assert isinstance(formatter, JsonFormatter)

