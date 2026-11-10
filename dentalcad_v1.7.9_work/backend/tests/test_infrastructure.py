import json
import logging

from app.json_logging import JsonFormatter


def test_json_formatter_emits_structured_request_fields():
    record = logging.LogRecord('test', logging.INFO, __file__, 12, 'http_request', (), None)
    record.request_id = 'req-1'
    record.method = 'GET'
    record.path = '/health'
    record.status_code = 200
    record.duration_ms = 1.5
    item = json.loads(JsonFormatter().format(record))
    assert item['message'] == 'http_request'
    assert item['request_id'] == 'req-1'
    assert item['status_code'] == 200


def test_settings_has_safe_docs_default():
    from app.settings import settings
    assert settings.debug_docs is False
    assert settings.max_requests_per_minute > 0
