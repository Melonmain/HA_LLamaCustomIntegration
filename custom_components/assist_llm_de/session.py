"""Session reset manager for Assist LLM (Deutsch)."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from homeassistant.components.conversation.const import ChatLogEventType
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import chat_session
from homeassistant.helpers.event import async_call_later

_LOGGER = logging.getLogger(__name__)

_DATA_CHAT_SESSION = getattr(chat_session, "DATA_CHAT_SESSION", None)
_CURRENT_SESSION_VAR = getattr(chat_session, "current_session", None)

try:
    from homeassistant.components.conversation.chat_log import (
        DATA_CHAT_LOGS as _DATA_CHAT_LOGS,
        async_subscribe_chat_logs as _async_subscribe_chat_logs,
    )
except ImportError:
    _DATA_CHAT_LOGS = None
    _async_subscribe_chat_logs = None


@callback
def async_clear_idle_sessions(hass: HomeAssistant) -> int:
    """Clear all idle Home Assistant chat sessions immediately."""
    if _DATA_CHAT_SESSION is None:
        _LOGGER.warning("chat_session.DATA_CHAT_SESSION is unavailable")
        return 0

    all_sessions = hass.data.get(_DATA_CHAT_SESSION)
    if not all_sessions:
        return 0

    cleared = 0
    for conversation_id, session in list(all_sessions.items()):
        if not session.in_use:
            all_sessions.pop(conversation_id, None)
            session.async_cleanup()
            cleared += 1
    return cleared


class SessionResetManager:
    """Clears completed chat sessions automatically unless awaiting a follow-up."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        reset_history: bool,
        keep_history_on_followup: bool,
    ) -> None:
        """Initialize the session reset manager."""
        self.hass = hass
        self.reset_history = reset_history
        self.keep_history_on_followup = keep_history_on_followup
        self._tracked_conversations: set[str] = set()
        self._pending_timers: dict[str, CALLBACK_TYPE] = {}
        self._unsub_chat_logs: CALLBACK_TYPE | None = None

    @callback
    def async_start(self) -> None:
        """Subscribe to chat log events if automatic reset is enabled."""
        if not self.reset_history:
            return
        if (
            _DATA_CHAT_SESSION is None
            or _CURRENT_SESSION_VAR is None
            or _async_subscribe_chat_logs is None
        ):
            _LOGGER.warning(
                "Automatic conversation reset disabled: internal Home Assistant "
                "chat session APIs are unavailable"
            )
            return
        self._unsub_chat_logs = _async_subscribe_chat_logs(
            self.hass, self._handle_chat_log_event
        )

    @callback
    def async_stop(self) -> None:
        """Unsubscribe from events and cancel all pending cleanup timers."""
        if self._unsub_chat_logs is not None:
            self._unsub_chat_logs()
            self._unsub_chat_logs = None
        for cancel in self._pending_timers.values():
            cancel()
        self._pending_timers.clear()
        self._tracked_conversations.clear()

    @callback
    def track_current_session(self) -> None:
        """Track the active conversation session for post-turn cleanup."""
        if not self.reset_history or _CURRENT_SESSION_VAR is None:
            return
        session = _CURRENT_SESSION_VAR.get()
        if session is None:
            return
        self._tracked_conversations.add(session.conversation_id)
        self._schedule_check(session.conversation_id, delay=0)

    @callback
    def _handle_chat_log_event(
        self,
        conversation_id: str,
        event_type: ChatLogEventType,
        data: dict[str, Any],
    ) -> None:
        """React to chat log updates for tracked conversations."""
        if event_type == ChatLogEventType.DELETED:
            if (cancel := self._pending_timers.pop(conversation_id, None)) is not None:
                cancel()
            self._tracked_conversations.discard(conversation_id)
            return

        if conversation_id not in self._tracked_conversations:
            return

        if event_type in (ChatLogEventType.CONTENT_ADDED, ChatLogEventType.UPDATED):
            self._schedule_check(conversation_id, delay=0)

    @callback
    def _schedule_check(self, conversation_id: str, delay: float) -> None:
        """Schedule a cleanup check for a tracked conversation."""
        if (existing := self._pending_timers.pop(conversation_id, None)) is not None:
            existing()

        @callback
        def _on_timer(_now: datetime) -> None:
            self._try_cleanup_conversation(conversation_id)

        self._pending_timers[conversation_id] = async_call_later(
            self.hass, delay, _on_timer
        )

    @callback
    def _try_cleanup_conversation(self, conversation_id: str) -> None:
        """Clean up a session if idle and not waiting for a follow-up answer."""
        self._pending_timers.pop(conversation_id, None)

        if _DATA_CHAT_SESSION is None:
            self._tracked_conversations.discard(conversation_id)
            return

        all_sessions = self.hass.data.get(_DATA_CHAT_SESSION)
        if not all_sessions or (session := all_sessions.get(conversation_id)) is None:
            self._tracked_conversations.discard(conversation_id)
            return

        all_chat_logs = (
            self.hass.data.get(_DATA_CHAT_LOGS) if _DATA_CHAT_LOGS is not None else None
        )
        chat_log = all_chat_logs.get(conversation_id) if all_chat_logs else None

        if session.in_use > 0 or (chat_log is not None and chat_log.turn_active):
            self._schedule_check(conversation_id, delay=1.0)
            return

        is_followup = chat_log is not None and bool(chat_log.continue_conversation)
        if self.keep_history_on_followup and is_followup:
            _LOGGER.debug(
                "Keeping session %s alive for follow-up question", conversation_id
            )
            return

        all_sessions.pop(conversation_id, None)
        session.async_cleanup()
        self._tracked_conversations.discard(conversation_id)
        _LOGGER.debug("Cleared completed conversation session %s", conversation_id)
