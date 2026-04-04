"""GeoView PySide6 shared bilingual infrastructure.

This module intentionally stays lightweight:
- per-app LanguageManager instances can be created by GeoViewApp
- a module-level default manager is also provided for simple shared use
- apps without i18n calls can ignore it safely
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, Signal


class LanguageManager(QObject):
    """App-level language manager with registry-backed translations."""

    language_changed = Signal(str)

    def __init__(self, parent: QObject | None = None, default_lang: str = "ko"):
        super().__init__(parent)
        self._lang = self._normalize_lang(default_lang)
        self._translations: dict[str, dict[str, str]] = {"ko": {}, "en": {}}

    @staticmethod
    def _normalize_lang(lang: str | None) -> str:
        normalized = str(lang or "ko").strip().lower()
        if normalized.startswith("en"):
            return "en"
        return "ko"

    @property
    def lang(self) -> str:
        return self._lang

    def set_lang(self, lang: str) -> bool:
        """Set current language. Returns True when the language changed."""
        normalized = self._normalize_lang(lang)
        if normalized == self._lang:
            return False
        self._lang = normalized
        self.language_changed.emit(self._lang)
        return True

    def toggle(self) -> bool:
        """Toggle between Korean and English."""
        return self.set_lang("en" if self._lang == "ko" else "ko")

    def register(self, translations: dict[str, dict[str, str]] | None) -> bool:
        """Register app-specific translation keys.

        Expected shape:
            {
                "ko": {"hello": "안녕하세요"},
                "en": {"hello": "Hello"},
            }
        """
        if not translations:
            return False

        changed = False
        for lang, entries in translations.items():
            normalized = self._normalize_lang(lang)
            if not isinstance(entries, dict):
                continue
            target = self._translations.setdefault(normalized, {})
            for key, value in entries.items():
                if value is None:
                    continue
                skey = str(key)
                svalue = str(value)
                if target.get(skey) != svalue:
                    target[skey] = svalue
                    changed = True
        return changed

    def t(self, key: str, default: str | None = None) -> str:
        """Translate a key with fallback to the opposite language and then raw key."""
        skey = str(key)
        value = self._translations.get(self._lang, {}).get(skey)
        if value is None:
            fallback_lang = "en" if self._lang == "ko" else "ko"
            value = self._translations.get(fallback_lang, {}).get(skey)
        if value is None:
            return skey if default is None else default
        return value

    def snapshot(self) -> dict[str, Any]:
        """Return a serializable snapshot useful for debugging or tests."""
        return {
            "lang": self._lang,
            "translations": {
                "ko": dict(self._translations.get("ko", {})),
                "en": dict(self._translations.get("en", {})),
            },
        }


_DEFAULT_LANGUAGE_MANAGER = LanguageManager()


def get_language_manager() -> LanguageManager:
    return _DEFAULT_LANGUAGE_MANAGER


def lang() -> str:
    return _DEFAULT_LANGUAGE_MANAGER.lang


def set_lang(value: str) -> bool:
    return _DEFAULT_LANGUAGE_MANAGER.set_lang(value)


def toggle_lang() -> bool:
    return _DEFAULT_LANGUAGE_MANAGER.toggle()


def t(key: str, default: str | None = None) -> str:
    return _DEFAULT_LANGUAGE_MANAGER.t(key, default)


def register_translations(translations: dict[str, dict[str, str]] | None) -> bool:
    return _DEFAULT_LANGUAGE_MANAGER.register(translations)


on_lang_change = _DEFAULT_LANGUAGE_MANAGER.language_changed

