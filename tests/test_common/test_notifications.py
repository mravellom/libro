"""Tests for notification system."""

import logging

from libro.common.notifications import (
    NotifyLevel,
    configure,
    notify,
    notify_upload_failed,
    notify_daily_summary,
)


def test_notify_logs_when_no_channels(caplog):
    """When no channels configured, notifications go to log."""
    configure()  # empty config
    with caplog.at_level(logging.INFO):
        result = notify("test message", NotifyLevel.INFO, "Test")
    assert not result  # no channel sent
    assert "test message" in caplog.text


def test_notify_error_level(caplog):
    configure()
    with caplog.at_level(logging.ERROR):
        notify("something broke", NotifyLevel.ERROR, "Error")
    assert "something broke" in caplog.text


def test_notify_upload_failed(caplog):
    configure()
    with caplog.at_level(logging.ERROR):
        notify_upload_failed(42, "timeout")
    assert "42" in caplog.text
    assert "timeout" in caplog.text


def test_notify_daily_summary(caplog):
    configure()
    with caplog.at_level(logging.INFO):
        notify_daily_summary(5, 12.50, 1)
    assert "5 books" in caplog.text
    assert "12.50" in caplog.text


def test_disabled_notifications():
    configure()
    from libro.common import notifications
    notifications._config.enabled = False
    result = notify("should not send", NotifyLevel.INFO)
    assert not result
    notifications._config.enabled = True  # reset
