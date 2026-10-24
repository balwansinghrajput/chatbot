import React from 'react';
import { BrainCircuit, Code2, FileText, Globe2, Image, Lightbulb, Paperclip } from 'lucide-react';
import { useChatStore } from '../store/chatStore';

const suggestions = [
  { icon: Globe2, title: 'Search the web', desc: 'Find real-time information', prompt: 'Search the web for the latest important AI developments.' },
  { icon: Paperclip, title: 'Analyze a file', desc: 'Upload docs, code, or data', prompt: 'Help me analyze a file and summarize the key findings.' },
  { icon: Image, title: 'Generate an image', desc: 'Create visual concepts', prompt: 'Help me create a detailed visual concept.' },
  { icon: Code2, title: 'Help me code', desc: 'Debug, refactor, or build', prompt: 'Help me build a clean, production-ready feature.' },
  { icon: Lightbulb, title: 'Explain something', desc: 'Break down complex topics', prompt: 'Explain a complex topic in clear, simple language.' },
  { icon: FileText, title: 'Research a topic', desc: 'Deep dives and synthesis', prompt: 'Research a topic deeply and synthesize the findings.' },
];

const WelcomeScreen: React.FC = () => {
  const { createChat, setActiveChat } = useChatStore();
  const choose = async (text: string) => { const id = await createChat(); void setActiveChat(id); window.dispatchEvent(new CustomEvent('suggestion-click', { detail: { text, chatId: id } })); };
  return <div className="welcome">
    <div className="welcome-glow" />
    <div className="ai-emblem"><BrainCircuit size={39} /></div>
    <h1>How can I help you today?</h1>
    <p>Your advanced AI assistant optimized for coding, research,<br className="desktop-break" /> analysis, and creative execution.</p>
    <div className="suggestion-grid">{suggestions.map(({ icon: Icon, title, desc, prompt }) => <button key={title} onClick={() => void choose(prompt)}><span className="suggestion-icon"><Icon size={20} /></span><span><strong>{title}</strong><small>{desc}</small></span></button>)}</div>
  </div>;
};

export default WelcomeScreen;
