import { create } from 'zustand';
import type { Chat, Message, ChatSettings, ThinkingLevel } from '../types';
import {
  apiListChats,
  apiCreateChat,
  apiDeleteChat,
  apiRenameChat,
  apiGetChat,
  type ApiChat,
} from '../lib/api';

// ─── Helpers ─────────────────────────────────────────────────────────────────

function apiChatToChat(apiChat: ApiChat, existingMessages?: Message[]): Chat {
  return {
    id: apiChat.id,
    title: apiChat.title,
    messages: existingMessages ?? apiChat.messages.map((m) => ({
      id: m.id,
      role: m.role,
      content: m.content,
      thinking: m.thinking ?? undefined,
      timestamp: new Date(m.timestamp),
      isStreaming: false,
    })),
    createdAt: new Date(apiChat.created_at),
    updatedAt: new Date(apiChat.updated_at),
  };
}

// ─── Store Interface ──────────────────────────────────────────────────────────

interface ChatStore {
  chats: Chat[];
  activeChatId: string | null;
  settings: ChatSettings;
  isSidebarOpen: boolean;
  isLoadingChats: boolean;

  // Remote operations
  loadChats: () => Promise<void>;
  createChat: () => Promise<string>;
  setActiveChat: (id: string) => Promise<void>;
  deleteChat: (id: string) => Promise<void>;
  renameChat: (id: string, title: string) => Promise<void>;

  // Local-only message mutations (during streaming)
  addMessage: (chatId: string, message: Omit<Message, 'id' | 'timestamp'>) => string;
  updateMessage: (chatId: string, messageId: string, update: Partial<Message>) => void;
  replaceStreamingMessage: (chatId: string, tempId: string, serverMessageId: string) => void;

  // Settings (local preference)
  setThinkingLevel: (level: ThinkingLevel) => void;
  setWebSearch: (enabled: boolean) => void;

  // UI
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;

  // Helpers
  getActiveChat: () => Chat | null;
}

// ─── Store Implementation ─────────────────────────────────────────────────────

export const useChatStore = create<ChatStore>()((set, get) => ({
  chats: [],
  activeChatId: null,
  settings: {
    thinkingLevel: 'medium',
    webSearch: false,
    model: 'thinkingmachines/inkling',
  },
  isSidebarOpen: true,
  isLoadingChats: false,

  loadChats: async () => {
    set({ isLoadingChats: true });
    try {
      const apiChats = await apiListChats();
      const currentChats = get().chats;
      const chats = apiChats.map((c) => {
        const existing = currentChats.find((curr) => curr.id === c.id);
        return apiChatToChat(c, existing?.messages);
      });
      set({ chats, isLoadingChats: false });
    } catch (err) {
      console.error('[store] loadChats failed:', err);
      set({ isLoadingChats: false });
    }
  },

  // ── Remote: create chat ───────────────────────────────────────────────────
  createChat: async () => {
    const apiChat = await apiCreateChat('New Chat');
    const chat = apiChatToChat(apiChat);
    set((state) => ({ chats: [chat, ...state.chats], activeChatId: chat.id }));
    return chat.id;
  },

  // ── Remote: switch active chat (load messages lazily) ─────────────────────
  setActiveChat: async (id: string) => {
    set({ activeChatId: id });
    const existing = get().chats.find((c) => c.id === id);
    // Only fetch messages if we don't have them yet
    if (existing && existing.messages.length === 0) {
      try {
        const apiChat = await apiGetChat(id);
        set((state) => ({
          chats: state.chats.map((c) =>
            c.id === id ? apiChatToChat(apiChat, undefined) : c
          ),
        }));
      } catch (err) {
        console.error('[store] setActiveChat fetch failed:', err);
      }
    }
  },

  // ── Remote: delete chat ───────────────────────────────────────────────────
  deleteChat: async (id: string) => {
    await apiDeleteChat(id);
    set((state) => {
      const chats = state.chats.filter((c) => c.id !== id);
      const activeChatId =
        state.activeChatId === id ? (chats[0]?.id ?? null) : state.activeChatId;
      return { chats, activeChatId };
    });
  },

  // ── Remote: rename chat ───────────────────────────────────────────────────
  renameChat: async (id: string, title: string) => {
    await apiRenameChat(id, title);
    set((state) => ({
      chats: state.chats.map((c) =>
        c.id === id ? { ...c, title } : c
      ),
    }));
  },

  // ── Local: add a temporary message (used during streaming) ───────────────
  addMessage: (chatId, message) => {
    const id = `tmp_${Date.now()}_${Math.random().toString(36).slice(2)}`;
    const msg: Message = { id, timestamp: new Date(), ...message };
    set((state) => ({
      chats: state.chats.map((c) =>
        c.id === chatId
          ? { ...c, messages: [...c.messages, msg], updatedAt: new Date() }
          : c
      ),
    }));
    return id;
  },

  // ── Local: patch a message in place (streaming updates) ──────────────────
  updateMessage: (chatId, messageId, update) =>
    set((state) => ({
      chats: state.chats.map((c) =>
        c.id === chatId
          ? {
              ...c,
              messages: c.messages.map((m) =>
                m.id === messageId ? { ...m, ...update } : m
              ),
            }
          : c
      ),
    })),

  // ── Local: swap temp ID with real server message ID after stream done ─────
  replaceStreamingMessage: (chatId, tempId, serverMessageId) =>
    set((state) => ({
      chats: state.chats.map((c) =>
        c.id === chatId
          ? {
              ...c,
              messages: c.messages.map((m) =>
                m.id === tempId
                  ? { ...m, id: serverMessageId, isStreaming: false }
                  : m
              ),
            }
          : c
      ),
    })),

  // ── Settings ──────────────────────────────────────────────────────────────
  setThinkingLevel: (level) =>
    set((state) => ({ settings: { ...state.settings, thinkingLevel: level } })),

  setWebSearch: (enabled) =>
    set((state) => ({ settings: { ...state.settings, webSearch: enabled } })),

  // ── UI ────────────────────────────────────────────────────────────────────
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
  setSidebarOpen: (open) => set({ isSidebarOpen: open }),

  getActiveChat: () => {
    const { chats, activeChatId } = get();
    return chats.find((c) => c.id === activeChatId) ?? null;
  },
}));
