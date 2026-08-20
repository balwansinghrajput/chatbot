import React, { useState } from 'react';
import { Globe, Brain, ChevronRight, Zap, Cpu, BookOpen } from 'lucide-react';
import { useChatStore } from '../store/chatStore';
import type { ThinkingLevel } from '../types';
import KnowledgePanel from './KnowledgePanel';

const thinkingOptions: { value: ThinkingLevel; label: string; icon: React.ReactNode; desc: string; color: string }[] = [
  { value: 'low', label: 'Quick', icon: <Zap size={12} />, desc: '1K tokens', color: 'text-emerald-400' },
  { value: 'medium', label: 'Balanced', icon: <Brain size={12} />, desc: '4K tokens', color: 'text-blue-400' },
  { value: 'high', label: 'Deep', icon: <Cpu size={12} />, desc: '8K tokens', color: 'text-purple-400' },
];

const ChatHeader: React.FC = () => {
  const { settings, setThinkingLevel, setWebSearch, isSidebarOpen, getActiveChat } = useChatStore();
  const activeChat = getActiveChat();
  const [kbOpen, setKbOpen] = useState(false);

  return (
    <>
      <header className={`fixed top-0 right-0 z-30 transition-all duration-300 ${isSidebarOpen ? 'left-72' : 'left-0'}`}>
        <div className="flex items-center justify-between px-4 py-3 bg-[#080d1a]/80 backdrop-blur-xl border-b border-white/5">
          {/* Chat title */}
          <div className="flex items-center gap-2 min-w-0">
            {!isSidebarOpen && <div className="w-10" />}
            <div className="min-w-0">
              <h2 className="text-sm font-semibold text-white truncate">
                {activeChat ? activeChat.title : 'M00'}
              </h2>
              <p className="text-xs text-slate-500 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse inline-block" />
                Online
              </p>
            </div>
          </div>

          {/* Controls */}
          <div className="flex items-center gap-2">
            {/* Knowledge Base Button */}
            <button
              onClick={() => setKbOpen(true)}
              title="Knowledge Base"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium transition-all duration-200 bg-white/5 border border-white/10 text-slate-400 hover:text-white hover:bg-purple-600/20 hover:border-purple-500/30"
            >
              <BookOpen size={13} className="text-purple-400" />
              <span className="hidden sm:inline">Knowledge</span>
            </button>

            {/* Web Search Toggle */}
            <button
              onClick={() => setWebSearch(!settings.webSearch)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium transition-all duration-200
                ${settings.webSearch
                  ? 'bg-blue-600/30 border border-blue-500/40 text-blue-300 shadow-lg shadow-blue-500/10'
                  : 'bg-white/5 border border-white/10 text-slate-400 hover:text-white hover:bg-white/10'
                }`}
            >
              <Globe size={13} className={settings.webSearch ? 'animate-spin-slow' : ''} />
              <span>Web Search</span>
              <span className={`w-1.5 h-1.5 rounded-full transition-colors ${settings.webSearch ? 'bg-blue-400' : 'bg-slate-600'}`} />
            </button>

            {/* Thinking Level */}
            <div className="flex items-center gap-1 bg-white/5 border border-white/10 rounded-xl p-1">
              <Brain size={12} className="text-slate-500 ml-1" />
              {thinkingOptions.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setThinkingLevel(opt.value)}
                  title={`${opt.label} – ${opt.desc}`}
                  className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium transition-all duration-200
                    ${settings.thinkingLevel === opt.value
                      ? `bg-blue-600 text-white shadow-md`
                      : 'text-slate-400 hover:text-white hover:bg-white/10'
                    }`}
                >
                  <span className={settings.thinkingLevel === opt.value ? 'text-white' : opt.color}>{opt.icon}</span>
                  {opt.label}
                </button>
              ))}
            </div>

            {/* Model badge */}
            <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 bg-white/5 border border-white/10 rounded-xl">
              <ChevronRight size={10} className="text-blue-400" />
              <span className="text-xs text-slate-400">M00</span>
            </div>
          </div>
        </div>
      </header>

      {/* Knowledge Base slide-in panel */}
      <KnowledgePanel isOpen={kbOpen} onClose={() => setKbOpen(false)} />
    </>
  );
};

export default ChatHeader;
