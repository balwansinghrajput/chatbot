import React, { useEffect, useRef, useState } from 'react';
import { ArrowUp, FileAudio, FileVideo, Globe2, Image, Mic, Paperclip, SlidersHorizontal, Square, X } from 'lucide-react';
import type { MediaAttachment } from '../types';

interface InputAreaProps { onSend: (message: string, attachments?: MediaAttachment[]) => void; isStreaming: boolean; onStop: () => void; disabled?: boolean; }

const LIMITS = { image: 10 * 1024 * 1024, audio: 20 * 1024 * 1024, video: 25 * 1024 * 1024 };
const kindFor = (mime: string): MediaAttachment['mediaType'] | null => mime.startsWith('image/') ? 'image' : mime.startsWith('audio/') ? 'audio' : mime.startsWith('video/') ? 'video' : null;
const readDataUrl = (file: File) => new Promise<string>((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(String(reader.result)); reader.onerror = () => reject(reader.error); reader.readAsDataURL(file); });

const InputArea: React.FC<InputAreaProps> = ({ onSend, isStreaming, onStop, disabled }) => {
  const [input, setInput] = useState('');
  const [attachments, setAttachments] = useState<MediaAttachment[]>([]);
  const [fileError, setFileError] = useState('');
  const textarea = useRef<HTMLTextAreaElement>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  useEffect(() => { if (textarea.current) { textarea.current.style.height = 'auto'; textarea.current.style.height = `${Math.min(textarea.current.scrollHeight, 180)}px`; } }, [input]);

  const addFiles = async (files: FileList | null) => {
    if (!files) return;
    setFileError('');
    const slots = Math.max(0, 4 - attachments.length);
    const selected = Array.from(files).slice(0, slots);
    if (files.length > slots) setFileError('You can attach up to 4 files.');
    const added: MediaAttachment[] = [];
    for (const file of selected) {
      const mediaType = kindFor(file.type);
      if (!mediaType) { setFileError('Supported files: PNG, JPEG, WebP, MP3, WAV, MP4, MOV, and WebM.'); continue; }
      if (file.size > LIMITS[mediaType]) { setFileError(`${file.name} is too large for ${mediaType} analysis.`); continue; }
      added.push({ id: `${Date.now()}-${file.name}-${Math.random()}`, name: file.name, mediaType, mimeType: file.type, dataUrl: await readDataUrl(file) });
    }
    setAttachments((current) => [...current, ...added].slice(0, 4));
    if (fileInput.current) fileInput.current.value = '';
  };

  const send = () => {
    if ((!input.trim() && !attachments.length) || isStreaming || disabled) return;
    const prompt = input.trim() || (attachments[0]?.mediaType === 'audio' ? 'Transcribe and summarize this audio.' : attachments[0]?.mediaType === 'video' ? 'Describe and summarize this video.' : 'Describe and analyze this image.');
    onSend(prompt, attachments);
    setInput(''); setAttachments([]); setFileError('');
  };

  return <div className="composer-wrap">
    <div className="composer">
      {attachments.length > 0 && <div className="attachment-tray">{attachments.map((attachment) => <div className="attachment-chip" key={attachment.id}>
        {attachment.mediaType === 'image' ? <img src={attachment.dataUrl} alt="" /> : <span>{attachment.mediaType === 'audio' ? <FileAudio /> : <FileVideo />}</span>}
        <div><strong>{attachment.name}</strong><small>{attachment.mediaType} · Nemotron Omni</small></div>
        <button onClick={() => setAttachments((items) => items.filter((item) => item.id !== attachment.id))} aria-label={`Remove ${attachment.name}`}><X /></button>
      </div>)}</div>}
      {fileError && <div className="composer-file-error">{fileError}</div>}
      <textarea ref={textarea} rows={1} value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }} placeholder={isStreaming ? 'M00 is thinking…' : attachments.length ? 'Ask about your media…' : 'Message M00…'} disabled={disabled || isStreaming} />
      <div className="composer-toolbar"><div>
        <input ref={fileInput} type="file" hidden multiple accept="image/png,image/jpeg,image/webp,audio/mpeg,audio/wav,audio/x-wav,video/mp4,video/quicktime,video/webm" onChange={(e) => void addFiles(e.target.files)} />
        <button title="Attach image, audio, or video" onClick={() => fileInput.current?.click()} disabled={disabled || isStreaming}><Paperclip size={19} /></button><button title="Web search"><Globe2 size={19} /></button><button title="Image generation"><Image size={19} /></button><button title="Tools"><SlidersHorizontal size={19} /></button>
      </div><div><button title="Voice input" disabled><Mic size={19} /></button>{isStreaming ? <button className="send-button stop" onClick={onStop}><Square size={14} fill="currentColor" /></button> : <button className="send-button" onClick={send} disabled={(!input.trim() && !attachments.length) || disabled}><ArrowUp size={21} /></button>}</div></div>
    </div>
    <p className="disclaimer">M00 can make mistakes. Verify important info.</p>
  </div>;
};

export default InputArea;
