import React, { useState } from 'react';
import {
  MessageSquarePlus,
  Trash2,
  ChevronLeft,
  ChevronRight,
  Bot,
  MoreVertical,
  Pencil,
  Check,
  X,
} from 'lucide-react';
import { useChatStore } from '../store/chatStore';
import type { Chat } from '../types';

const formatTime = (date: Date) => {
  const d = new Date(date);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  const days = Math.floor(diff / 86400000);
  if (days === 0) return 'Today';
  if (days === 1) return 'Yesterday';
  if (days < 7) return `${days}d ago`;
  return d.toLocaleDateString();
};

interface ChatItemProps {
  chat: Chat;
  isActive: boolean;
  onSelect: () => void;
  onDelete: () => void;
  onRename: (title: string) => void;
}

const ChatItem: React.FC<ChatItemProps> = ({ chat, isActive, onSelect, onDelete, onRename }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(chat.title);
  const [showMenu, setShowMenu] = useState(false);

  const handleRename = () => {
    if (editTitle.trim()) {
      onRename(editTitle.trim());
    }
    setIsEditing(false);
    setShowMenu(false);
  };

  return (
    <div
      className={`group relative flex items-center gap-2 px-3 py-2.5 rounded-xl cursor-pointer transition-all duration-200 mb-1
        ${isActive
          ? 'bg-blue-600/20 border border-blue-500/30 shadow-lg shadow-blue-500/10'
          : 'hover:bg-white/5 border border-transparent'
        }`}
      onClick={!isEditing ? onSelect : undefined}
    >
      <div className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center
        ${isActive ? 'bg-blue-500/30' : 'bg-white/5'}`}>
        <Bot size={14} className={isActive ? 'text-blue-400' : 'text-slate-400'} />
      </div>

      <div className="flex-1 min-w-0">
        {isEditing ? (
          <input
            autoFocus
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleRename();
              if (e.key === 'Escape') { setIsEditing(false); setEditTitle(chat.title); }
            }}
            className="w-full bg-transparent text-sm text-white outline-none border-b border-blue-400 pb-0.5"
            onClick={(e) => e.stopPropagation()}
          />
        ) : (
          <p className={`text-sm truncate font-medium ${isActive ? 'text-white' : 'text-slate-300'}`}>
            {chat.title}
          </p>
        )}
        <p className="text-xs text-slate-500 mt-0.5">{formatTime(chat.updatedAt)}</p>
      </div>

      {isEditing ? (
        <div className="flex gap-1 flex-shrink-0" onClick={(e) => e.stopPropagation()}>
          <button onClick={handleRename} className="p-1 rounded text-green-400 hover:bg-green-500/20">
            <Check size={12} />
          </button>
          <button onClick={() => { setIsEditing(false); setEditTitle(chat.title); }} className="p-1 rounded text-red-400 hover:bg-red-500/20">
            <X size={12} />
          </button>
        </div>
      ) : (
        <div className="relative flex-shrink-0">
          <button
            onClick={(e) => { e.stopPropagation(); setShowMenu(!showMenu); }}
            className={`p-1 rounded-lg transition-opacity ${showMenu ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'} hover:bg-white/10 text-slate-400`}
          >
            <MoreVertical size={14} />
          </button>
          {showMenu && (
            <div className="absolute right-0 top-7 z-50 bg-[#0f1729] border border-white/10 rounded-xl shadow-2xl py-1 w-36 overflow-hidden">
              <button
                onClick={(e) => { e.stopPropagation(); setIsEditing(true); setShowMenu(false); }}
                className="flex items-center gap-2 w-full px-3 py-2 text-xs text-slate-300 hover:bg-white/5 hover:text-white transition-colors"
              >
                <Pencil size={12} /> Rename
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); onDelete(); setShowMenu(false); }}
                className="flex items-center gap-2 w-full px-3 py-2 text-xs text-red-400 hover:bg-red-500/10 hover:text-red-300 transition-colors"
              >
                <Trash2 size={12} /> Delete
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const Sidebar: React.FC = () => {
  const { chats, activeChatId, isSidebarOpen, isLoadingChats, createChat, setActiveChat, deleteChat, renameChat, toggleSidebar } = useChatStore();

  const today = chats.filter(c => {
    const d = new Date(c.updatedAt);
    return new Date().toDateString() === d.toDateString();
  });
  const older = chats.filter(c => {
    const d = new Date(c.updatedAt);
    return new Date().toDateString() !== d.toDateString();
  });

  return (
    <>
      {/* Collapsed toggle */}
      {!isSidebarOpen && (
        <button
          onClick={toggleSidebar}
          className="fixed left-4 top-4 z-50 w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/30 hover:bg-blue-500 transition-all"
        >
          <ChevronRight size={18} className="text-white" />
        </button>
      )}

      {/* Sidebar */}
      <aside
        className={`fixed left-0 top-0 h-full z-40 flex flex-col transition-all duration-300 ease-in-out
          ${isSidebarOpen ? 'w-72 translate-x-0' : 'w-72 -translate-x-full'}
          bg-[#080d1a] border-r border-white/5`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-4 border-b border-white/5">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center shadow-lg shadow-blue-500/30">
              <Bot size={16} className="text-white" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-white tracking-tight">M00</h1>
              <p className="text-xs text-slate-500">by Balwan Singh Rajput</p>
            </div>
          </div>
          <button
            onClick={toggleSidebar}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-all"
          >
            <ChevronLeft size={16} />
          </button>
        </div>

        {/* New Chat Button */}
        <div className="px-3 py-3">
          <button
            onClick={() => void createChat()}
            className="w-full flex items-center gap-2.5 px-3 py-2.5 bg-blue-600 hover:bg-blue-500 rounded-xl text-white text-sm font-medium transition-all duration-200 shadow-lg shadow-blue-500/20 group"
          >
            <MessageSquarePlus size={16} className="group-hover:rotate-12 transition-transform duration-200" />
            New Conversation
          </button>
        </div>

        {/* Chat List */}
        <div className="flex-1 overflow-y-auto px-3 pb-4 space-y-1 scrollbar-thin">
          {isLoadingChats && (
            <div className="flex items-center justify-center py-8">
              <div className="w-5 h-5 rounded-full border-2 border-blue-500/30 border-t-blue-500 animate-spin" />
            </div>
          )}

          {!isLoadingChats && chats.length === 0 && (
            <div className="text-center py-12">
              <div className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center mx-auto mb-3">
                <MessageSquarePlus size={20} className="text-slate-500" />
              </div>
              <p className="text-sm text-slate-500">No conversations yet</p>
              <p className="text-xs text-slate-600 mt-1">Start a new chat above</p>
            </div>
          )}

          {today.length > 0 && (
            <>
              <p className="text-xs text-slate-600 font-semibold px-2 pt-2 pb-1 uppercase tracking-wider">Today</p>
              {today.map((chat) => (
                <ChatItem
                  key={chat.id}
                  chat={chat}
                  isActive={chat.id === activeChatId}
                  onSelect={() => void setActiveChat(chat.id)}
                  onDelete={() => void deleteChat(chat.id)}
                  onRename={(title) => void renameChat(chat.id, title)}
                />
              ))}
            </>
          )}

          {older.length > 0 && (
            <>
              <p className="text-xs text-slate-600 font-semibold px-2 pt-3 pb-1 uppercase tracking-wider">Earlier</p>
              {older.map((chat) => (
                <ChatItem
                  key={chat.id}
                  chat={chat}
                  isActive={chat.id === activeChatId}
                  onSelect={() => void setActiveChat(chat.id)}
                  onDelete={() => void deleteChat(chat.id)}
                  onRename={(title) => void renameChat(chat.id, title)}
                />
              ))}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-white/5">
          <p className="text-xs text-slate-600 text-center">M00 &copy; Balwan Singh Rajput</p>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
