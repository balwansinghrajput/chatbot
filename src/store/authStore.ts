import { create } from 'zustand';
import * as auth from '../lib/auth';
import type { AuthUser } from '../lib/auth';

type AuthStatus = 'idle' | 'loading' | 'authenticated' | 'anonymous';

interface AuthState {
  user: AuthUser | null;
  status: AuthStatus;
  checkSession: () => Promise<void>;
  login: (input: Parameters<typeof auth.login>[0]) => Promise<void>;
  signup: (input: Parameters<typeof auth.signup>[0]) => Promise<void>;
  logout: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  status: 'idle',
  checkSession: async () => {
    set({ status: 'loading' });
    try {
      const user = await auth.currentUser();
      set({ user, status: user ? 'authenticated' : 'anonymous' });
    } catch {
      set({ user: null, status: 'anonymous' });
    }
  },
  login: async (input) => {
    const user = await auth.login(input);
    set({ user, status: 'authenticated' });
  },
  signup: async (input) => {
    const user = await auth.signup(input);
    set({ user, status: 'authenticated' });
  },
  logout: async () => {
    await auth.logout();
    set({ user: null, status: 'anonymous' });
  },
}));
