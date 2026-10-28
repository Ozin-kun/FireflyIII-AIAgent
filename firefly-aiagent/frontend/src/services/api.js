import { API_ENDPOINTS } from '../constants/api.js';

async function getJson(endpoint) {
  const response = await fetch(endpoint);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  return response.json();
}

export function fetchUser() {
  return getJson(API_ENDPOINTS.user);
}

export function fetchHealth() {
  return getJson(API_ENDPOINTS.health);
}

export function fetchMemory() {
  return getJson(API_ENDPOINTS.memory);
}

export function streamChat(payload) {
  return fetch(API_ENDPOINTS.chatStream, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}
