import { useState } from 'react';
import { fetchMemory } from '../services/api.js';

export function useMemory() {
  const [memoryStats, setMemoryStats] = useState(null);
  const [facts, setFacts] = useState([]);
  const [showMemoryModal, setShowMemoryModal] = useState(false);

  async function openMemory() {
    try {
      const data = await fetchMemory();
      setFacts(data.facts || []);
      setMemoryStats(data.stats || {});
      setShowMemoryModal(true);
    } catch (error) {
      console.warn('Could not fetch memory:', error);
    }
  }

  return {
    memoryStats,
    facts,
    showMemoryModal,
    openMemory,
    closeMemory: () => setShowMemoryModal(false),
  };
}
