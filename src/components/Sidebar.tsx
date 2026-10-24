import React, { useState } from 'react';
import { Check, ChevronLeft, ChevronRight, LogOut, MoreHorizontal, Pencil, Plus, Settings, Trash2, User, X } from 'lucide-react';
import { useChatStore } from '../store/chatStore';
import { useAuthStore } from '../store/authStore';
import type { Chat } from '../types';

type Group = { label: string; chats: Chat[] };

function groupChats(chats: Chat[]): Group[] {
  const now = new Date();
  const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const groups: Group[] = [
    { label: 'Today', chats: [] },
    { label: 'Yesterday', chats: [] },
    { label: 'Previous 7 days', chats: [] },
    { label: 'Previous 30 days', chats: [] },
    { label: 'Earlier', chats: [] },
  ];
  chats.forEach((chat) => {
    const days = Math.floor((startToday - new Date(chat.updatedAt).getTime()) / 86400000);
    const index = days <= 0 ? 0 : days === 1 ? 1 : days <= 7 ? 2 : days <= 30 ? 3 : 4;
    groups[index].chats.push(chat);
  });
  return groups.filter((group) => group.chats.length);
}

const ChatItem = ({ chat, active }: { chat: Chat; active: boolean }) => {
  const { setActiveChat, deleteChat, renameChat, setSidebarOpen } = useChatStore();
  const [menu, setMenu] = useState(false);
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(chat.title);

  const save = () => {
    if (title.trim()) void renameChat(chat.id, title.trim());
    setEditing(false);
    setMenu(false);
  };

  return (
    <div className={`chat-row group ${active ? 'active' : ''}`} onClick={() => { void setActiveChat(chat.id); if (window.innerWidth < 768) setSidebarOpen(false); }}>
      {editing ? (
        <input autoFocus value={title} onChange={(e) => setTitle(e.target.value)} onClick={(e) => e.stopPropagation()}
          onKeyDown={(e) => { if (e.key === 'Enter') save(); if (e.key === 'Escape') setEditing(false); }} />
      ) : <span>{chat.title}</span>}
      <div className="chat-actions" onClick={(e) => e.stopPropagation()}>
        {editing ? <><button onClick={save}><Check size={13} /></button><button onClick={() => setEditing(false)}><X size={13} /></button></> : (
          <button onClick={() => setMenu(!menu)} aria-label="Chat actions"><MoreHorizontal size={15} /></button>
        )}
        {menu && !editing && <div className="chat-menu">
          <button onClick={() => { setEditing(true); setMenu(false); }}><Pencil size={13} /> Rename</button>
          <button className="danger" onClick={() => void deleteChat(chat.id)}><Trash2 size={13} /> Delete</button>
        </div>}
      </div>
    </div>
  );
};

const Sidebar: React.FC = () => {
  const { chats, activeChatId, isSidebarOpen, isLoadingChats, createChat, toggleSidebar } = useChatStore();
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const signOut = async () => {
    await logout();
    window.location.replace('/login');
  };
  return <>
    {!isSidebarOpen && <button className="sidebar-open" onClick={toggleSidebar} aria-label="Open sidebar"><ChevronRight size={20} /></button>}
    {isSidebarOpen && <button className="sidebar-scrim" onClick={toggleSidebar} aria-label="Close sidebar" />}
    <aside className={`sidebar ${isSidebarOpen ? 'open' : ''}`}>
      <div className="brand-row">
        <div className="brand"><div className="brand-mark">M∞</div><span>M00</span></div>
        <button className="icon-button" onClick={toggleSidebar} aria-label="Collapse sidebar"><ChevronLeft size={20} /></button>
      </div>
      <button className="new-chat" onClick={() => void createChat()}><Plus size={21} /> New Chat</button>
      <nav className="chat-list">
        {isLoadingChats && <div className="loading-ring" />}
        {!isLoadingChats && chats.length === 0 && <p className="empty-history">Your conversations will appear here.</p>}
        {groupChats(chats).map((group) => <section key={group.label}>
          <h3>{group.label}</h3>
          {group.chats.map((chat) => <ChatItem key={chat.id} chat={chat} active={chat.id === activeChatId} />)}
        </section>)}
      </nav>
      <div className="sidebar-footer">
        <button className="settings-link"><Settings size={20} /> Settings</button>
        <div className="profile-card"><div className="avatar"><User size={17} /></div><div><strong>{user?.name ?? 'M00 User'}</strong><small>{user?.role ?? user?.email}</small></div><button className="profile-logout" onClick={() => void signOut()} aria-label="Sign out" title="Sign out"><LogOut size={18} /></button></div>
      </div>
    </aside>
  </>;
};

export default Sidebar;
