import React from 'react';
import { MessageSquare, Sparkles, Globe, Brain, Zap } from 'lucide-react';
import { useChatStore } from '../store/chatStore';

const WelcomeScreen: React.FC = () => {
  const { createChat, setActiveChat } = useChatStore();

  const suggestions = [
    { icon: <Globe size={16} />, text: 'What are the latest advancements in AI?', color: 'text-blue-400' },
    { icon: <Brain size={16} />, text: 'Explain quantum computing in simple terms', color: 'text-purple-400' },
    { icon: <Zap size={16} />, text: 'Write a Python script to analyze CSV data', color: 'text-emerald-400' },
    { icon: <Sparkles size={16} />, text: 'Help me brainstorm a business idea', color: 'text-amber-400' },
  ];

  const handleSuggestion = async (text: string) => {
    const id = await createChat();
    void setActiveChat(id);
    // The parent App will handle sending this via a custom event
    window.dispatchEvent(new CustomEvent('suggestion-click', { detail: { text, chatId: id } }));
  };

  return (
    <div className="flex flex-col items-center justify-center h-full px-8 text-center">
      {/* Logo */}
      <div className="relative mb-6">
        <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-blue-500 via-blue-600 to-blue-800 flex items-center justify-center shadow-2xl shadow-blue-500/30">
          <MessageSquare size={36} className="text-white" />
        </div>
        <div className="absolute -top-1 -right-1 w-6 h-6 bg-gradient-to-br from-purple-400 to-purple-600 rounded-full flex items-center justify-center shadow-lg">
          <Sparkles size={12} className="text-white" />
        </div>
      </div>

      <h2 className="text-3xl font-bold text-white mb-2 tracking-tight">
        How can I help you today?
      </h2>
      <p className="text-slate-400 text-sm mb-10 max-w-md">
        I'm powered by <span className="text-blue-400 font-medium">thinkingmachines/inkling</span> via NVIDIA. 
        Ask me anything — I reason deeply before answering.
      </p>

      {/* Suggestion chips */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-2xl">
        {suggestions.map((s, i) => (
          <button
            key={i}
            onClick={() => handleSuggestion(s.text)}
            className="flex items-start gap-3 text-left p-4 bg-[#0f1729] border border-white/8 rounded-2xl hover:border-blue-500/30 hover:bg-blue-600/5 transition-all duration-200 group shadow-lg"
          >
            <span className={`mt-0.5 flex-shrink-0 ${s.color} group-hover:scale-110 transition-transform`}>{s.icon}</span>
            <span className="text-sm text-slate-300 group-hover:text-white transition-colors leading-relaxed">{s.text}</span>
          </button>
        ))}
      </div>

      <p className="text-xs text-slate-600 mt-8">
        Toggle <span className="text-slate-500">Web Search</span> and <span className="text-slate-500">Thinking Level</span> in the toolbar above
      </p>
    </div>
  );
};

export default WelcomeScreen;
