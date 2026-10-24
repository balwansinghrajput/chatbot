export interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: string | null;
  created_at: string;
}

interface AuthResponse { user: AuthUser }

async function request(path: string, init?: RequestInit): Promise<AuthResponse> {
  const response = await fetch(`/api/auth${path}`, {
    ...init,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Authentication failed (${response.status})`);
  }
  return response.json();
}

export async function signup(input: {
  name: string; email: string; password: string; role: string;
  accepted_terms: boolean; remember: boolean;
}): Promise<AuthUser> {
  return (await request('/signup', { method: 'POST', body: JSON.stringify(input) })).user;
}

export async function login(input: { email: string; password: string; remember: boolean }): Promise<AuthUser> {
  return (await request('/login', { method: 'POST', body: JSON.stringify(input) })).user;
}

export async function currentUser(): Promise<AuthUser | null> {
  const response = await fetch('/api/auth/me', { credentials: 'include' });
  if (response.status === 401) return null;
  if (!response.ok) throw new Error(`Session check failed (${response.status})`);
  return ((await response.json()) as AuthResponse).user;
}

export async function logout(): Promise<void> {
  const response = await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
  if (!response.ok && response.status !== 204) throw new Error('Could not sign out');
}
