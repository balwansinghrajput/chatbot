import React from 'react';
import { Brain } from 'lucide-react';

const ThinkingIndicator: React.FC = () => {
  return (
    <div className="flex gap-3 mb-6">
      {/* Avatar */}
      <div className="flex-shrink-0 w-8 h-8 rounded-xl bg-gradient-to-br from-slate-700 to-slate-800 border border-white/10 flex items-center justify-center shadow-lg">
        <Brain size={14} className="text-purple-400 animate-pulse" />
      </div>

      <div className="flex flex-col gap-2">
        {/* Thinking label */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-purple-950/40 border border-purple-500/20 rounded-xl">
            <div className="flex gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
            <span className="text-xs text-purple-400 font-medium">Thinking...</span>
          </div>
        </div>

        {/* Shimmer placeholder */}
        <div className="flex flex-col gap-2 px-4 py-3 bg-[#0f1729] border border-white/8 rounded-2xl rounded-tl-sm max-w-xs">
          <div className="h-2.5 bg-white/5 rounded-full w-48 animate-pulse" />
          <div className="h-2.5 bg-white/5 rounded-full w-32 animate-pulse" style={{ animationDelay: '150ms' }} />
          <div className="h-2.5 bg-white/5 rounded-full w-40 animate-pulse" style={{ animationDelay: '300ms' }} />
        </div>
      </div>
    </div>
  );
};

export default ThinkingIndicator;
