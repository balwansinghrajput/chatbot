import React, { useEffect, useRef, useCallback, useState } from 'react';
import Sidebar from './components/Sidebar';
import ChatHeader from './components/ChatHeader';
import MessageBubble from './components/MessageBubble';
import ThinkingIndicator from './components/ThinkingIndicator';
import InputArea from './components/InputArea';
import WelcomeScreen from './components/WelcomeScreen';
import LandingPage from './components/LandingPage';
import AuthPage from './components/AuthPage';
import AuthGuard from './components/AuthGuard';
import { useChatStore } from './store/chatStore';
import { streamMessage, type MessagePayload } from './lib/api';
import type { MediaAttachment } from './types';

const ChatApp: React.FC = () => {
  const {
    activeChatId,
    isSidebarOpen,
    settings,
    loadChats,
    createChat,
    addMessage,
    updateMessage,
    replaceStreamingMessage,
    renameChat,
    getActiveChat,
  } = useChatStore();

  const [isStreaming, setIsStreaming] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const activeChat = getActiveChat();

  // ── Load chats from backend on mount ────────────────────────────────────
  useEffect(() => {
    loadChats();
  }, [loadChats]);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [activeChat?.messages.length, isThinking, scrollToBottom]);

  // ── Send message ─────────────────────────────────────────────────────────
  const handleSend = useCallback(
    async (content: string, overrideChatId?: string, attachments: MediaAttachment[] = []) => {
      let targetChatId = overrideChatId ?? activeChatId;

      // Create a new chat in the backend if needed
      if (!targetChatId) {
        targetChatId = await createChat();
      }

      // Auto-title on first message
      const chat = useChatStore.getState().chats.find((c) => c.id === targetChatId);
      if (chat && chat.messages.length === 0) {
        const title = content.slice(0, 50) + (content.length > 50 ? '...' : '');
        renameChat(targetChatId, title); // optimistic UI update (backend also auto-titles)
      }

      // Add user message optimistically to local store for immediate display
      addMessage(targetChatId, { role: 'user', content, attachments });

      // Add placeholder assistant message
      const tempAssistantId = addMessage(targetChatId, {
        role: 'assistant',
        content: '',
        isStreaming: true,
      });

      setIsThinking(true);
      setIsStreaming(true);

      // Build message history to send (exclude the temp assistant slot)
      const currentMessages: MessagePayload[] = useChatStore
        .getState()
        .chats.find((c) => c.id === targetChatId)
        ?.messages.filter((m) => m.id !== tempAssistantId)
        .map((m) => ({ role: m.role, content: m.content })) ?? [];

      // Create abort controller for this request
      abortControllerRef.current = new AbortController();

      let accContent = '';
      let accThinking = '';
      await streamMessage(
        targetChatId,
        currentMessages,
        settings.thinkingLevel,
        // onThinking
        (chunk) => {
          accThinking += chunk;
          updateMessage(targetChatId!, tempAssistantId, {
            thinking: accThinking,
            isStreaming: true,
          });
          scrollToBottom();
        },
        // onContent
        (chunk) => {
          setIsThinking(false);
          accContent += chunk;
          updateMessage(targetChatId!, tempAssistantId, {
            content: accContent,
            thinking: accThinking || undefined,
            isStreaming: true,
          });
          scrollToBottom();
        },
        // onDone
        (serverMessageId) => {
          setIsThinking(false);
          setIsStreaming(false);
          if (serverMessageId) {
            replaceStreamingMessage(targetChatId!, tempAssistantId, serverMessageId);
          } else {
            updateMessage(targetChatId!, tempAssistantId, { isStreaming: false });
          }
          // Refresh chat list so sidebar title/timestamp updates
          loadChats();
        },
        // onError
        (err) => {
          setIsThinking(false);
          setIsStreaming(false);
          updateMessage(targetChatId!, tempAssistantId, {
            content: `❌ **Error:** ${err}`,
            isStreaming: false,
          });
        },
        // onSources
        (sources) => {
          updateMessage(targetChatId!, tempAssistantId, {
            sources,
            isStreaming: true,
          });
        },
        // onImages
        (images) => {
          updateMessage(targetChatId!, tempAssistantId, {
            images,
            isStreaming: true,
          });
        },
        // onLinkedIn
        (profile) => {
          updateMessage(targetChatId!, tempAssistantId, {
            linkedinProfile: profile,
            isStreaming: true,
          });
        },
        // onMapRoute
        (route) => {
          updateMessage(targetChatId!, tempAssistantId, {
            mapRoute: route,
            isStreaming: true,
          });
        },
        abortControllerRef.current.signal,
        attachments,
      );
    },
    [
      activeChatId,
      settings,
      createChat,
      addMessage,
      updateMessage,
      replaceStreamingMessage,
      renameChat,
      loadChats,
      scrollToBottom,
    ]
  );

  // ── Stop streaming ───────────────────────────────────────────────────────
  const handleStop = useCallback(() => {
    abortControllerRef.current?.abort();
    setIsStreaming(false);
    setIsThinking(false);
    if (activeChatId) {
      const chat = useChatStore.getState().chats.find((c) => c.id === activeChatId);
      const lastMsg = chat?.messages[chat.messages.length - 1];
      if (lastMsg?.isStreaming) {
        updateMessage(activeChatId, lastMsg.id, { isStreaming: false });
      }
    }
  }, [activeChatId, updateMessage]);

  // ── Suggestion chip handler from WelcomeScreen ───────────────────────────
  useEffect(() => {
    const handler = async (e: Event) => {
      const { text, chatId } = (e as CustomEvent).detail;
      await handleSend(text, chatId);
    };
    window.addEventListener('suggestion-click', handler);
    return () => window.removeEventListener('suggestion-click', handler);
  }, [handleSend]);

  const hasMessages = activeChat && activeChat.messages.length > 0;

  return (
    <div className="app-shell">
      {/* Sidebar */}
      <Sidebar />

      {/* Main content */}
      <div
        className={`main-shell ${isSidebarOpen ? 'sidebar-visible' : ''}`}
      >
        {/* Header */}
        <ChatHeader />

        {/* Messages */}
        <main className={`chat-main ${hasMessages ? 'has-messages' : ''}`}>
          {!activeChatId || !hasMessages ? (
            <WelcomeScreen />
          ) : (
            <div className="message-list">
              {activeChat.messages.map((message) => (
                <MessageBubble key={message.id} message={message} />
              ))}
              {isThinking && <ThinkingIndicator />}
              <div ref={messagesEndRef} />
            </div>
          )}
        </main>

        {/* Input */}
        <div className="input-dock">
          <InputArea
            onSend={(message, attachments) => handleSend(message, undefined, attachments)}
            isStreaming={isStreaming}
            onStop={handleStop}
            disabled={false}
          />
        </div>
      </div>
    </div>
  );
};

const App: React.FC = () => {
  const path = window.location.pathname;
  if (path.startsWith('/app')) return <AuthGuard><ChatApp /></AuthGuard>;
  if (path === '/login') return <AuthPage mode="login" />;
  if (path === '/signup') return <AuthPage mode="signup" />;
  return <LandingPage />;
};

export default App;
