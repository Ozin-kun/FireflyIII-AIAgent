import { useState } from 'react';
import { STORAGE_KEYS } from '../constants/api.js';
import {
  createSessionId,
  getInitialSessionState,
  getSessionFromStorage,
  saveSessions,
} from '../utils/chat.js';

function getStoredSessionState() {
  return getInitialSessionState(getSessionFromStorage(STORAGE_KEYS.chatSessions));
}

export function useChatSessions() {
  const [sessions, setSessions] = useState(() => getSessionFromStorage(STORAGE_KEYS.chatSessions));
  const [activeSessionId, setActiveSessionId] = useState(
    () => getStoredSessionState().activeSessionId
  );
  const [messages, setMessages] = useState(() => getStoredSessionState().messages);

  const createNewSession = () => {
    const freshId = createSessionId();
    setActiveSessionId(freshId);
    setMessages([]);
    return freshId;
  };

  const selectSession = (sessionId) => {
    const target = sessions.find((session) => session.id === sessionId);
    if (!target) return false;

    setActiveSessionId(target.id);
    setMessages(target.messages || []);
    return true;
  };

  const deleteSession = (sessionId) => {
    const remaining = sessions.filter((session) => session.id !== sessionId);
    setSessions(remaining);
    saveSessions(STORAGE_KEYS.chatSessions, remaining);

    if (sessionId !== activeSessionId) return;

    if (remaining.length > 0) {
      setActiveSessionId(remaining[0].id);
      setMessages(remaining[0].messages || []);
    } else {
      setActiveSessionId(createSessionId());
      setMessages([]);
    }
  };

  return {
    sessions,
    setSessions,
    activeSessionId,
    messages,
    setMessages,
    createNewSession,
    selectSession,
    deleteSession,
  };
}
