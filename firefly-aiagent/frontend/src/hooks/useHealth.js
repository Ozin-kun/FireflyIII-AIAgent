import { useEffect, useState } from 'react';
import { fetchHealth, fetchUser } from '../services/api.js';

const INITIAL_USER = { email: '', role: '', id: null };
const INITIAL_HEALTH = { status: 'checking', firefly_status: 'checking' };

export function useHealth() {
  const [user, setUser] = useState(INITIAL_USER);
  const [health, setHealth] = useState(INITIAL_HEALTH);

  async function refreshHealthAndUser() {
    try {
      const userData = await fetchUser();
      if (userData.success && userData.user && userData.user.email) {
        setUser(userData.user);
      }

      const healthData = await fetchHealth();
      setHealth(healthData);
      if (healthData.user && healthData.user.email) {
        setUser((previousUser) => ({ ...previousUser, ...healthData.user }));
      }
    } catch (error) {
      console.warn('Backend connecting...', error);
    }
  }

  useEffect(() => {
    // Health and user data must be loaded once when the app mounts.
    // eslint-disable-next-line react/set-state-in-effect
    refreshHealthAndUser();
  }, []);

  return { user, health, refreshHealthAndUser };
}
