import React, { useState } from 'react';
import { BrainCircuit, ChevronDown, Share2, SlidersHorizontal, User } from 'lucide-react';
import { useChatStore } from '../store/chatStore';
import type { ThinkingLevel } from '../types';
import KnowledgePanel from './KnowledgePanel';

const ChatHeader: React.FC = () => {
  const { settings, setThinkingLevel, isSidebarOpen } = useChatStore();
  const [modelsOpen, setModelsOpen] = useState(false);
  const [kbOpen, setKbOpen] = useState(false);
  const options: { value: ThinkingLevel; label: string }[] = [{ value: 'low', label: 'Quick' }, { value: 'medium', label: 'Balanced' }, { value: 'high', label: 'Deep' }];
  return <>
    <header className={`topbar ${isSidebarOpen ? 'sidebar-visible' : ''}`}>
      <div className="model-picker-wrap">
        <button className="model-picker" onClick={() => setModelsOpen(!modelsOpen)}><BrainCircuit size={20} /> <span>M00 · Inkling</span><ChevronDown size={16} /></button>
        {modelsOpen && <div className="model-menu"><p>Reasoning mode</p>{options.map((opt) => <button key={opt.value} className={settings.thinkingLevel === opt.value ? 'selected' : ''} onClick={() => { setThinkingLevel(opt.value); setModelsOpen(false); }}>{opt.label}<small>{opt.value === 'low' ? 'Fast responses' : opt.value === 'medium' ? 'Best balance' : 'Maximum reasoning'}</small></button>)}</div>}
      </div>
      <div className="topbar-actions">
        <button className="share-button"><Share2 size={17} /><span>Share</span></button>
        <button className="icon-button solid" onClick={() => setKbOpen(true)} title="Knowledge and tools"><SlidersHorizontal size={19} /></button>
        <div className="avatar"><User size={17} /></div>
      </div>
    </header>
    <KnowledgePanel isOpen={kbOpen} onClose={() => setKbOpen(false)} />
  </>;
};

export default ChatHeader;
