import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Bot, User, ChevronDown, ChevronRight, Copy, Check, Globe, ExternalLink, Image as ImageIcon, X, ZoomIn } from 'lucide-react';
import type { Message } from '../types';

interface MessageBubbleProps {
  message: Message;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user';
  const [thinkingExpanded, setThinkingExpanded] = useState(false);
  const [copied, setCopied] = useState(false);
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null);
  const [lightboxTitle, setLightboxTitle] = useState<string>('');
  const [failedImages, setFailedImages] = useState<Set<number>>(new Set());

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleImageError = (index: number) => {
    setFailedImages((prev) => new Set(prev).add(index));
  };

  const validImages = message.images?.filter((_, i) => !failedImages.has(i)) ?? [];

  return (
    <div className={`flex gap-3 group ${isUser ? 'flex-row-reverse' : 'flex-row'} mb-6`}>
      {/* Avatar */}
      <div className={`flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center shadow-lg
        ${isUser
          ? 'bg-gradient-to-br from-blue-500 to-blue-700 shadow-blue-500/30'
          : 'bg-gradient-to-br from-slate-700 to-slate-800 border border-white/10'
        }`}>
        {isUser
          ? <User size={14} className="text-white" />
          : <Bot size={14} className="text-blue-400" />
        }
      </div>

      <div className={`flex flex-col gap-2 max-w-[75%] ${isUser ? 'items-end' : 'items-start'}`}>
        {/* Thinking block */}
        {message.thinking && (
          <div className="w-full bg-purple-950/30 border border-purple-500/20 rounded-xl overflow-hidden">
            <button
              onClick={() => setThinkingExpanded(!thinkingExpanded)}
              className="w-full flex items-center gap-2 px-3 py-2 text-xs text-purple-400 hover:bg-purple-500/10 transition-colors"
            >
              <div className="flex items-center gap-1.5 flex-1">
                {thinkingExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                <span className="font-medium">Reasoning process</span>
                <span className="text-purple-500/70 ml-auto">{message.thinking.split(' ').length} words</span>
              </div>
            </button>
            {thinkingExpanded && (
              <div className="px-3 pb-3">
                <div className="text-xs text-purple-300/70 leading-relaxed font-mono whitespace-pre-wrap border-t border-purple-500/10 pt-2">
                  {message.thinking}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Image Gallery */}
        {!isUser && validImages.length > 0 && (
          <div className="w-full">
            <div className="flex items-center gap-1.5 mb-2.5">
              <ImageIcon size={12} className="text-violet-400" />
              <span className="text-xs text-slate-400 font-medium">Images</span>
              <span className="text-xs text-slate-600 ml-1">· {validImages.length} found</span>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {validImages.slice(0, 6).map((img, i) => (
                <div
                  key={i}
                  className="relative aspect-square rounded-xl overflow-hidden cursor-pointer group/img bg-white/5 border border-white/8 hover:border-violet-500/40 transition-all duration-200 shadow-lg hover:shadow-violet-500/10"
                  onClick={() => { setLightboxUrl(img.url); setLightboxTitle(img.title); }}
                >
                  <img
                    src={img.thumbnail || img.url}
                    alt={img.title}
                    className="w-full h-full object-cover transition-transform duration-300 group-hover/img:scale-110"
                    onError={() => handleImageError(i)}
                    loading="lazy"
                  />
                  {/* Hover overlay */}
                  <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent opacity-0 group-hover/img:opacity-100 transition-opacity duration-200 flex items-end justify-between p-2">
                    <span className="text-xs text-white/80 truncate leading-tight line-clamp-2 max-w-[80%]">
                      {img.title}
                    </span>
                    <ZoomIn size={14} className="text-white flex-shrink-0" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Message bubble */}
        <div className={`relative px-4 py-3 rounded-2xl shadow-lg
          ${isUser
            ? 'bg-gradient-to-br from-blue-600 to-blue-700 text-white rounded-tr-sm shadow-blue-500/20'
            : 'bg-[#0f1729] border border-white/8 text-slate-100 rounded-tl-sm'
          }`}>
          {message.isStreaming && !message.content && (
            <div className="flex items-center gap-1.5 py-1">
              <span className="w-2 h-2 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-2 h-2 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-2 h-2 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          )}

          {message.content && (
            <div className={`prose prose-sm max-w-none ${isUser ? 'prose-invert' : 'prose-invert prose-slate'}`}>
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  code: ({ className, children, ...props }) => {
                    const isBlock = className?.includes('language-');
                    if (isBlock) {
                      return (
                        <div className="relative group/code my-2">
                          <pre className="bg-black/40 border border-white/10 rounded-xl p-3 overflow-x-auto text-xs">
                            <code className={className} {...props}>{children}</code>
                          </pre>
                        </div>
                      );
                    }
                    return (
                      <code className="bg-white/10 px-1.5 py-0.5 rounded text-xs font-mono" {...props}>
                        {children}
                      </code>
                    );
                  },
                  a: ({ href, children }) => (
                    <a href={href} target="_blank" rel="noopener noreferrer"
                      className="text-blue-400 hover:text-blue-300 underline underline-offset-2">
                      {children}
                    </a>
                  ),
                  table: ({ children }) => (
                    <div className="overflow-x-auto rounded-xl border border-white/10 my-2">
                      <table className="min-w-full text-xs">{children}</table>
                    </div>
                  ),
                  th: ({ children }) => <th className="px-3 py-2 bg-white/5 text-left font-semibold border-b border-white/10">{children}</th>,
                  td: ({ children }) => <td className="px-3 py-2 border-b border-white/5">{children}</td>,
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}

          {/* Streaming cursor */}
          {message.isStreaming && message.content && (
            <span className="inline-block w-0.5 h-4 bg-blue-400 animate-pulse ml-0.5 align-text-bottom" />
          )}
        </div>

        {/* Sources panel — shown for assistant messages with web search results */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="w-full mt-1">
            <div className="flex items-center gap-1.5 mb-2">
              <Globe size={11} className="text-blue-400" />
              <span className="text-xs text-slate-500 font-medium">Sources</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {message.sources.map((src, i) => (
                <a
                  key={i}
                  href={src.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  title={src.title}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 bg-white/5 hover:bg-blue-500/10 border border-white/8 hover:border-blue-500/30 rounded-xl transition-all duration-150 group/src max-w-[200px]"
                >
                  <img
                    src={`https://www.google.com/s2/favicons?domain=${src.domain}&sz=32`}
                    alt=""
                    width={14}
                    height={14}
                    className="rounded-sm flex-shrink-0"
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = 'none';
                    }}
                  />
                  <span className="text-xs text-slate-400 group-hover/src:text-blue-300 truncate transition-colors">
                    {src.domain}
                  </span>
                  <ExternalLink size={9} className="text-slate-600 group-hover/src:text-blue-400 flex-shrink-0 transition-colors" />
                </a>
              ))}
            </div>
          </div>
        )}

        {/* Actions */}
        {!message.isStreaming && message.content && (
          <div className={`flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity ${isUser ? 'flex-row-reverse' : ''}`}>
            <button
              onClick={handleCopy}
              className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300 transition-colors px-2 py-1 rounded-lg hover:bg-white/5"
            >
              {copied ? <Check size={11} className="text-emerald-400" /> : <Copy size={11} />}
              {copied ? 'Copied' : 'Copy'}
            </button>
            <span className="text-xs text-slate-600">
              {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>
        )}
      </div>

      {/* Lightbox */}
      {lightboxUrl && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
          onClick={() => setLightboxUrl(null)}
        >
          <div
            className="relative max-w-4xl max-h-[90vh] rounded-2xl overflow-hidden shadow-2xl border border-white/10"
            onClick={(e) => e.stopPropagation()}
          >
            <img
              src={lightboxUrl}
              alt={lightboxTitle}
              className="max-w-full max-h-[85vh] object-contain"
            />
            {lightboxTitle && (
              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent px-4 py-3">
                <p className="text-sm text-white/90 truncate">{lightboxTitle}</p>
              </div>
            )}
            <button
              className="absolute top-3 right-3 w-8 h-8 rounded-full bg-black/50 hover:bg-black/80 flex items-center justify-center text-white transition-colors"
              onClick={() => setLightboxUrl(null)}
            >
              <X size={16} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default MessageBubble;
