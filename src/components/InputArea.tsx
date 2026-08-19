import React, { useState, useRef, useEffect } from 'react';
import { Send, Square, Paperclip, Mic } from 'lucide-react';

interface InputAreaProps {
  onSend: (message: string) => void;
  isStreaming: boolean;
  onStop: () => void;
  disabled?: boolean;
}

const InputArea: React.FC<InputAreaProps> = ({ onSend, isStreaming, onStop, disabled }) => {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming || disabled) return;
    onSend(trimmed);
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="px-4 pb-4 pt-2">
      <div className={`relative flex flex-col bg-[#0f1729] border rounded-2xl shadow-2xl transition-all duration-200
        ${disabled ? 'border-white/5 opacity-60' : 'border-white/10 hover:border-blue-500/30 focus-within:border-blue-500/50 focus-within:shadow-blue-500/10'}`}>

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled || isStreaming}
          placeholder={isStreaming ? 'AI is responding...' : 'Ask me anything... (Shift+Enter for newline)'}
          rows={1}
          className="w-full bg-transparent text-sm text-white placeholder-slate-500 resize-none px-4 pt-3.5 pb-2 outline-none leading-relaxed"
          style={{ maxHeight: '200px' }}
        />

        {/* Bottom bar */}
        <div className="flex items-center justify-between px-3 pb-2.5">
          <div className="flex items-center gap-1">
            <button
              disabled
              className="p-1.5 rounded-lg text-slate-600 cursor-not-allowed"
              title="Attach file (coming soon)"
            >
              <Paperclip size={15} />
            </button>
            <button
              disabled
              className="p-1.5 rounded-lg text-slate-600 cursor-not-allowed"
              title="Voice input (coming soon)"
            >
              <Mic size={15} />
            </button>
          </div>

          <div className="flex items-center gap-2">
            {input.length > 0 && (
              <span className="text-xs text-slate-600">{input.length}</span>
            )}

            {isStreaming ? (
              <button
                onClick={onStop}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-red-600/20 border border-red-500/30 rounded-xl text-xs text-red-400 hover:bg-red-600/30 transition-all"
              >
                <Square size={11} fill="currentColor" />
                Stop
              </button>
            ) : (
              <button
                onClick={handleSend}
                disabled={!input.trim() || disabled}
                className={`w-8 h-8 flex items-center justify-center rounded-xl transition-all duration-200
                  ${input.trim() && !disabled
                    ? 'bg-blue-600 text-white hover:bg-blue-500 shadow-lg shadow-blue-500/30'
                    : 'bg-white/5 text-slate-600 cursor-not-allowed'
                  }`}
              >
                <Send size={14} className={input.trim() ? 'translate-x-px' : ''} />
              </button>
            )}
          </div>
        </div>
      </div>

      <p className="text-center text-xs text-slate-700 mt-2">
        InklingAI can make mistakes. Verify important information.
      </p>
    </div>
  );
};

export default InputArea;
