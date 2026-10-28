import { EMPTY_SESSION_TITLE, SESSION_ID_PREFIX } from '../constants/chat.js';

export function createSessionId() {
  return `${SESSION_ID_PREFIX}${Date.now()}`;
}

export function createSessionTitle(text) {
  return text.length > 28 ? `${text.slice(0, 28)}...` : text;
}

export function getSessionFromStorage(storageKey) {
  try {
    const saved = localStorage.getItem(storageKey);
    if (!saved) return [];

    const parsed = JSON.parse(saved);
    return Array.isArray(parsed) ? parsed : [];
  } catch (error) {
    console.warn('Could not read sessions from localStorage:', error);
    return [];
  }
}

export function saveSessions(storageKey, sessions) {
  try {
    localStorage.setItem(storageKey, JSON.stringify(sessions));
  } catch {
    // Keep the in-memory session state when browser storage is unavailable.
  }
}

export function getInitialSessionState(sessions) {
  const firstSession = sessions[0];
  return {
    activeSessionId: firstSession?.id || createSessionId(),
    messages: firstSession?.messages || [],
  };
}

export function upsertSession(sessions, sessionId, messages, firstMessage) {
  let found = false;
  const updated = sessions.map((session) => {
    if (session.id !== sessionId) return session;

    found = true;
    return {
      ...session,
      title:
        session.title && session.title !== EMPTY_SESSION_TITLE
          ? session.title
          : createSessionTitle(firstMessage),
      messages,
      updatedAt: Date.now(),
    };
  });

  if (!found) {
    updated.unshift({
      id: sessionId,
      title: createSessionTitle(firstMessage),
      createdAt: new Date().toLocaleDateString('id-ID', {
        day: 'numeric',
        month: 'short',
      }),
      updatedAt: Date.now(),
      messages,
    });
  }

  return updated.sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
}
