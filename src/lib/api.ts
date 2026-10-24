/**
 * Backend API client
 * All requests go through Vite's /api proxy → http://localhost:8000
 */

import type { ThinkingLevel, MediaAttachment } from '../types';

const BASE = '/api';

// ─── Types matching backend responses ────────────────────────────────────────

export interface ApiMessage {
  id: string;
  chat_id: string;
  role: 'user' | 'assistant';
  content: string;
  thinking?: string | null;
  timestamp: string;
}

export interface ApiChat {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: ApiMessage[];
}

// ─── Chat CRUD ───────────────────────────────────────────────────────────────

export async function apiListChats(): Promise<ApiChat[]> {
  const res = await fetch(`${BASE}/chats`, { credentials: 'include' });
  if (!res.ok) throw new Error(`Failed to list chats: ${res.status}`);
  return res.json();
}

export async function apiCreateChat(title = 'New Chat'): Promise<ApiChat> {
  const res = await fetch(`${BASE}/chats`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error(`Failed to create chat: ${res.status}`);
  return res.json();
}

export async function apiGetChat(chatId: string): Promise<ApiChat> {
  const res = await fetch(`${BASE}/chats/${chatId}`, { credentials: 'include' });
  if (!res.ok) throw new Error(`Failed to get chat: ${res.status}`);
  return res.json();
}

export async function apiRenameChat(chatId: string, title: string): Promise<ApiChat> {
  const res = await fetch(`${BASE}/chats/${chatId}`, {
    method: 'PATCH',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error(`Failed to rename chat: ${res.status}`);
  return res.json();
}

export async function apiDeleteChat(chatId: string): Promise<void> {
  const res = await fetch(`${BASE}/chats/${chatId}`, { method: 'DELETE', credentials: 'include' });
  if (!res.ok && res.status !== 204) throw new Error(`Failed to delete chat: ${res.status}`);
}

// ─── Scraping ────────────────────────────────────────────────────────────────

export interface UrlContext {
  url: string;
  title: string;
  content: string;
  page_type: string;
}

export interface ScrapeResponse extends UrlContext {
  metadata: Record<string, unknown>;
  char_count: number;
}

export async function apiScrapeUrl(url: string, maxChars = 10000): Promise<ScrapeResponse> {
  const res = await fetch(`${BASE}/scrape`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, max_chars: maxChars }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Scraping failed' }));
    throw new Error(err.detail ?? `Server error ${res.status}`);
  }
  return res.json();
}

// ─── SSE Streaming ───────────────────────────────────────────────────────────

export interface StreamEvent {
  type: 'thinking' | 'content' | 'done' | 'error' | 'sources' | 'images' | 'linkedin' | 'map_route';
  text?: string;
  message_id?: string;
  sources?: SearchSource[];
  images?: ImageResult[];
  profile?: any;
  origin?: string;
  destination?: string;
}

export interface ImageResult {
  url: string;
  thumbnail: string;
  title: string;
  source: string;
  width: number;
  height: number;
}

export interface SearchSource {
  title: string;
  href: string;
  body: string;
  domain: string;
}

export interface MessagePayload {
  role: 'user' | 'assistant';
  content: string;
}

export async function streamMessage(
  chatId: string,
  messages: MessagePayload[],
  thinkingLevel: ThinkingLevel,
  onThinking: (chunk: string) => void,
  onContent: (chunk: string) => void,
  onDone: (messageId: string) => void,
  onError: (err: string) => void,
  onSources: (sources: SearchSource[]) => void,
  onImages: (images: ImageResult[]) => void,
  onLinkedIn?: (profile: any) => void,
  onMapRoute?: (route: any) => void,
  signal?: AbortSignal,
  attachments: MediaAttachment[] = [],
): Promise<void> {
  let response: Response;

  try {
    response = await fetch(`${BASE}/chats/${chatId}/stream`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages,
        thinking_level: thinkingLevel,
        attachments: attachments.map((attachment) => ({
          name: attachment.name,
          media_type: attachment.mediaType,
          mime_type: attachment.mimeType,
          data_url: attachment.dataUrl,
        })),
      }),
      signal,
    });
  } catch (err) {
    if ((err as Error).name === 'AbortError') return;
    onError((err as Error).message);
    return;
  }

  if (!response.ok) {
    onError(`Server error ${response.status}`);
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) { onError('No response body'); return; }

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const raw = line.slice(6).trim();
        if (!raw) continue;

        try {
          const event: StreamEvent = JSON.parse(raw);
          if (event.type === 'images' && event.images) {
            onImages(event.images);
          } else if (event.type === 'sources' && event.sources) {
            onSources(event.sources);
          } else if (event.type === 'linkedin' && event.profile && onLinkedIn) {
            onLinkedIn(event.profile);
          } else if (event.type === 'map_route' && event.origin && event.destination && onMapRoute) {
            onMapRoute({ origin: event.origin, destination: event.destination });
          } else if (event.type === 'thinking' && event.text) {
            onThinking(event.text);
          } else if (event.type === 'content' && event.text) {
            onContent(event.text);
          } else if (event.type === 'done') {
            onDone(event.message_id ?? '');
            return;
          } else if (event.type === 'error') {
            onError(event.text ?? 'Unknown error');
            return;
          }
        } catch {
          // skip malformed SSE lines
        }
      }
    }
  } catch (err) {
    if ((err as Error).name !== 'AbortError') {
      onError((err as Error).message);
    }
  } finally {
    reader.releaseLock();
  }
}
