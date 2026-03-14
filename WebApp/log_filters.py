import logging
import re


class SensitiveDataFilter(logging.Filter):
    """Фильтр для скрытия чувствительных данных в логах"""

    PATTERNS = [
        (re.compile(r'(password["\s:=]+)["\']?[^"\',\s]+', re.IGNORECASE), r'\1***'),
        (re.compile(r'(token["\s:=]+)["\']?[^"\',\s]+', re.IGNORECASE), r'\1***'),
        (re.compile(r'(secret["\s:=]+)["\']?[^"\',\s]+', re.IGNORECASE), r'\1***'),
        (re.compile(r'(eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)'), '***JWT***'),
    ]

    def filter(self, record):
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            for pattern, replacement in self.PATTERNS:
                record.msg = pattern.sub(replacement, record.msg)
        return True