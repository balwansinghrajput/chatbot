import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Bot, User, Copy, Check, Globe, ExternalLink, Image as ImageIcon, X, ZoomIn, Map as MapIcon } from 'lucide-react';
import type { Message } from '../types';

interface MessageBubbleProps {
  message: Message;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null);
  const [lightboxTitle, setLightboxTitle] = useState<string>('');
  const [failedImages, setFailedImages] = useState<Set<string>>(new Set());

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleImageError = (url: string) => {
    setFailedImages((prev) => new Set(prev).add(url));
  };

  const validImages = message.images?.filter((image) => !failedImages.has(image.url)) ?? [];

  // The parent renders the single shared ThinkingIndicator while an assistant
  // response has no visible output yet. Avoid rendering a second empty avatar
  // and bubble for the temporary streaming message.
  const hasVisibleOutput = Boolean(
    message.content || validImages.length || message.sources?.length ||
    message.linkedinProfile || message.mapRoute
  );
  if (!isUser && message.isStreaming && !hasVisibleOutput) return null;

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
        {isUser && message.attachments && message.attachments.length > 0 && (
          <div className="message-attachments">
            {message.attachments.map((attachment) => attachment.mediaType === 'image' ? (
              <img key={attachment.id} src={attachment.dataUrl} alt={attachment.name} title={attachment.name} />
            ) : (
              <div key={attachment.id} className="message-media-file">
                {attachment.mediaType === 'audio' ? 'Audio' : 'Video'} · {attachment.name}
              </div>
            ))}
          </div>
        )}
        {/* LinkedIn Profile Block */}
        {!isUser && message.linkedinProfile && (
          <div className="w-full">
            <div className="flex items-center gap-1.5 mb-2.5">
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[#0a66c2]"><path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"></path><rect width="4" height="12" x="2" y="9"></rect><circle cx="4" cy="4" r="2"></circle></svg>
              <span className="text-xs text-slate-400 font-medium">LinkedIn Profile</span>
            </div>
            
            <a 
              href={message.linkedinProfile.profile_url}
              target="_blank"
              rel="noopener noreferrer"
              className="group block relative overflow-hidden rounded-xl border border-[#0a66c2]/30 bg-slate-800/80 hover:bg-[#0a66c2]/10 transition-all duration-300 shadow-[0_0_15px_-5px_rgba(10,102,194,0.3)] hover:shadow-[0_0_25px_-5px_rgba(10,102,194,0.4)]"
            >
              {/* Premium gradient overlay */}
              <div className="absolute inset-0 bg-gradient-to-br from-[#0a66c2]/10 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              
              <div className="p-4 flex gap-4 items-start relative z-10">
                {/* Photo */}
                <div className="flex-shrink-0">
                  <div className="w-16 h-16 rounded-full overflow-hidden border-2 border-[#0a66c2]/50 p-0.5">
                    {message.linkedinProfile.photo_url ? (
                      <img 
                        src={message.linkedinProfile.photo_url} 
                        alt={message.linkedinProfile.name}
                        className="w-full h-full object-cover rounded-full bg-slate-900"
                        onError={(e) => {
                          (e.target as HTMLImageElement).src = `https://ui-avatars.com/api/?name=${encodeURIComponent(message.linkedinProfile!.name)}&background=0a66c2&color=fff&size=128`;
                        }}
                      />
                    ) : (
                      <div className="w-full h-full rounded-full bg-slate-900 flex items-center justify-center text-xl font-bold text-slate-400">
                        {message.linkedinProfile.name.charAt(0)}
                      </div>
                    )}
                  </div>
                </div>
                
                {/* Details */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <h3 className="text-sm font-semibold text-white truncate group-hover:text-blue-400 transition-colors">
                      {message.linkedinProfile.name}
                    </h3>
                    <ExternalLink size={14} className="text-slate-500 group-hover:text-blue-400 transition-colors flex-shrink-0" />
                  </div>
                  
                  <p className="text-xs text-blue-300/80 mb-2 line-clamp-2">
                    {message.linkedinProfile.headline}
                  </p>
                  
                  {message.linkedinProfile.snippet && (
                    <p className="text-[11px] text-slate-400 line-clamp-3 leading-relaxed border-l-2 border-[#0a66c2]/30 pl-2">
                      {message.linkedinProfile.snippet}
                    </p>
                  )}
                </div>
              </div>
            </a>
          </div>
        )}

        {/* Map Route Block */}
        {!isUser && message.mapRoute && (
          <div className="w-full">
            <div className="flex items-center gap-1.5 mb-2.5">
              <MapIcon size={12} className="text-emerald-500" />
              <span className="text-xs text-slate-400 font-medium">Route Map</span>
            </div>
            <div className="w-full h-64 rounded-xl overflow-hidden border border-white/10 shadow-lg relative bg-slate-900">
              <iframe 
                width="100%" 
                height="100%" 
                frameBorder="0" 
                style={{ border: 0 }} 
                src={`https://www.google.com/maps?saddr=${encodeURIComponent(message.mapRoute.origin)}&daddr=${encodeURIComponent(message.mapRoute.destination)}&output=embed`} 
                allowFullScreen
                loading="lazy"
              ></iframe>
            </div>
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
                    onError={(event) => {
                      const element = event.currentTarget;
                      if (!element.dataset.usedOriginal && img.url && img.thumbnail !== img.url) {
                        element.dataset.usedOriginal = 'true';
                        element.src = img.url;
                      } else {
                        handleImageError(img.url);
                      }
                    }}
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
