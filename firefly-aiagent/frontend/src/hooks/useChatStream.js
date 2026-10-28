import { useCallback, useState } from 'react';
import { STORAGE_KEYS } from '../constants/api.js';
import { streamChat } from '../services/api.js';
import { saveSessions, upsertSession } from '../utils/chat.js';

function updateAssistantMessage(messages, assistantId, update) {
  return messages.map((message) =>
    message.id === assistantId ? update(message) : message
  );
}

export function useChatStream({
  activeSessionId,
  messages,
  setMessages,
  setSessions,
  stopListening,
}) {
  const [loading, setLoading] = useState(false);

  const sendMessage = useCallback(
    async (textToSend) => {
      if (!textToSend.trim() || loading) return;

      stopListening();
      const currentSessionId = activeSessionId;
      const historyPayload = messages
        .filter((message) => message.content && !message.isStreaming)
        .map((message) => ({ role: message.role, content: message.content }));
      const userMessage = {
        id: Date.now().toString(),
        role: 'user',
        content: textToSend,
        timestamp: new Date().toLocaleTimeString([], {
          hour: '2-digit',
          minute: '2-digit',
        }),
      };
      const assistantId = (Date.now() + 1).toString();
      const initialAssistantMessage = {
        id: assistantId,
        role: 'assistant',
        content: '',
        plan: [],
        is_complex: false,
        actions: [],
        reflection: '',
        timestamp: new Date().toLocaleTimeString([], {
          hour: '2-digit',
          minute: '2-digit',
        }),
        isStreaming: true,
      };

      setMessages([...messages, userMessage, initialAssistantMessage]);
      setLoading(true);

      const applyStreamData = (data) => {
        if (data.type === 'token' && data.content) {
          setMessages((previousMessages) =>
            updateAssistantMessage(previousMessages, assistantId, (message) => ({
              ...message,
              content: message.content + data.content,
            }))
          );
        } else if (data.type === 'plan') {
          setMessages((previousMessages) =>
            updateAssistantMessage(previousMessages, assistantId, (message) => ({
              ...message,
              plan: data.plan || message.plan,
              is_complex:
                data.is_complex !== undefined ? data.is_complex : message.is_complex,
            }))
          );
        } else if (data.type === 'action' && data.action) {
          setMessages((previousMessages) =>
            updateAssistantMessage(previousMessages, assistantId, (message) => ({
              ...message,
              actions: [...(message.actions || []), data.action],
            }))
          );
        } else if (data.type === 'done') {
          setMessages((previousMessages) =>
            updateAssistantMessage(previousMessages, assistantId, (message) => ({
              ...message,
              isStreaming: false,
              content: message.content || data.reply || 'Tugas selesai dieksekusi.',
              plan: data.plan && data.plan.length > 0 ? data.plan : message.plan,
              actions:
                data.actions && data.actions.length > 0 ? data.actions : message.actions,
              reflection: data.reflection || message.reflection,
              is_complex:
                data.is_complex !== undefined ? data.is_complex : message.is_complex,
            }))
          );
        } else if (data.type === 'error') {
          setMessages((previousMessages) =>
            updateAssistantMessage(previousMessages, assistantId, (message) => ({
              ...message,
              isStreaming: false,
              content: message.content
                ? `${message.content}\n\n⚠️ ${data.reply || data.error}`
                : data.reply || `Terjadi kesalahan: ${data.error}`,
            }))
          );
        }
      };

      try {
        const response = await streamChat({
          message: textToSend,
          thread_id: currentSessionId,
          history: historyPayload,
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        if (!response.body) {
          throw new Error('ReadableStream tidak didukung pada browser ini');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split(/\r?\n/);
          buffer = lines.pop() || '';

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed.startsWith('data:')) continue;
            const jsonStr = trimmed.slice(5).trim();
            if (!jsonStr) continue;

            try {
              applyStreamData(JSON.parse(jsonStr));
            } catch (parseError) {
              console.warn('SSE parse error:', parseError, jsonStr);
            }
          }
        }

        if (buffer.trim().startsWith('data:')) {
          try {
            applyStreamData(JSON.parse(buffer.trim().slice(5).trim()));
          } catch (parseError) {
            console.warn('SSE parse error:', parseError, buffer);
          }
        }

        setMessages((previousMessages) => {
          const finalized = updateAssistantMessage(
            previousMessages,
            assistantId,
            (message) => ({
              ...message,
              isStreaming: false,
              content: message.content || 'Tugas selesai dieksekusi.',
            })
          );
          setSessions((previousSessions) => {
            const updated = upsertSession(
              previousSessions,
              currentSessionId,
              finalized,
              textToSend
            );
            saveSessions(STORAGE_KEYS.chatSessions, updated);
            return updated;
          });
          return finalized;
        });
      } catch (error) {
        console.error('Chat stream error:', error);
        setMessages((previousMessages) => {
          const finalized = updateAssistantMessage(
            previousMessages,
            assistantId,
            (message) => ({
              ...message,
              isStreaming: false,
              content: message.content
                ? `${message.content}\n\n⚠️ Terjadi kendala streaming: ${error.message}`
                : `Terjadi kendala saat menghubungi server: ${error.message}`,
            })
          );
          setSessions((previousSessions) => {
            const updated = previousSessions.map((session) =>
              session.id === currentSessionId
                ? { ...session, messages: finalized, updatedAt: Date.now() }
                : session
            );
            saveSessions(STORAGE_KEYS.chatSessions, updated);
            return updated;
          });
          return finalized;
        });
      } finally {
        setLoading(false);
      }
    },
    [activeSessionId, loading, messages, setMessages, setSessions, stopListening]
  );

  return { loading, sendMessage };
}
