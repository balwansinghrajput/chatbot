import React, { useState, useEffect, useCallback } from 'react';
import {
  BookOpen, Plus, Trash2, Search, X, ChevronDown, ChevronRight,
  Tag, Link2, FileText, Loader2, AlertCircle, CheckCircle2,
} from 'lucide-react';

interface KnowledgeChunk {
  id: string;
  title: string;
  content: string;
  source?: string;
  category?: string;
  created_at: string;
}

interface KnowledgePanelProps {
  isOpen: boolean;
  onClose: () => void;
}

const BASE = '/api/knowledge';

async function apiFetch(path: string, opts?: RequestInit) {
  const res = await fetch(`${BASE}${path}`, opts);
  if (!res.ok) throw new Error(`${res.status}`);
  if (res.status === 204) return null;
  return res.json();
}

// ── Chunk card ────────────────────────────────────────────────────────────────

const ChunkCard: React.FC<{ chunk: KnowledgeChunk; onDelete: (id: string) => void }> = ({ chunk, onDelete }) => {
  const [expanded, setExpanded] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    if (!confirm(`Delete "${chunk.title}"?`)) return;
    setDeleting(true);
    try {
      await apiFetch(`/${chunk.id}`, { method: 'DELETE' });
      onDelete(chunk.id);
    } catch {
      alert('Failed to delete chunk.');
      setDeleting(false);
    }
  };

  return (
    <div className="bg-white/4 border border-white/8 rounded-xl overflow-hidden transition-all hover:border-white/15">
      {/* Header */}
      <div
        className="flex items-start gap-3 p-3 cursor-pointer select-none"
        onClick={() => setExpanded((e) => !e)}
      >
        <div className="mt-0.5 text-blue-400 flex-shrink-0">
          <FileText size={14} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-white truncate">{chunk.title}</p>
          <div className="flex items-center gap-2 mt-0.5 flex-wrap">
            {chunk.category && (
              <span className="inline-flex items-center gap-1 text-[10px] text-blue-400 bg-blue-500/10 border border-blue-500/20 rounded-full px-2 py-0.5">
                <Tag size={9} /> {chunk.category}
              </span>
            )}
            {chunk.source && (
              <span className="inline-flex items-center gap-1 text-[10px] text-slate-500 truncate max-w-[140px]">
                <Link2 size={9} /> {chunk.source}
              </span>
            )}
            <span className="text-[10px] text-slate-600 ml-auto">
              {new Date(chunk.created_at).toLocaleDateString()}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          {expanded ? <ChevronDown size={14} className="text-slate-500" /> : <ChevronRight size={14} className="text-slate-500" />}
          <button
            onClick={(e) => { e.stopPropagation(); handleDelete(); }}
            disabled={deleting}
            className="p-1 rounded text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-colors"
          >
            {deleting ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
          </button>
        </div>
      </div>
      {/* Content */}
      {expanded && (
        <div className="px-3 pb-3 border-t border-white/5">
          <p className="text-xs text-slate-400 mt-2 whitespace-pre-wrap leading-relaxed line-clamp-10">
            {chunk.content}
          </p>
        </div>
      )}
    </div>
  );
};

// ── Add form ──────────────────────────────────────────────────────────────────

const AddForm: React.FC<{ onAdded: (chunk: KnowledgeChunk) => void; onCancel: () => void }> = ({ onAdded, onCancel }) => {
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [source, setSource] = useState('');
  const [category, setCategory] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !content.trim()) { setError('Title and content are required.'); return; }
    setSaving(true); setError('');
    try {
      const chunk = await apiFetch('', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: title.trim(), content: content.trim(), source: source.trim() || undefined, category: category.trim() || undefined }),
      });
      onAdded(chunk);
    } catch {
      setError('Failed to save. Check backend logs.');
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="bg-blue-600/10 border border-blue-500/20 rounded-xl p-4 space-y-3">
      <p className="text-xs font-semibold text-blue-300 uppercase tracking-wider">New Knowledge Chunk</p>
      <input
        value={title} onChange={(e) => setTitle(e.target.value)}
        placeholder="Title *"
        className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50"
      />
      <textarea
        value={content} onChange={(e) => setContent(e.target.value)}
        placeholder="Content (the knowledge text to embed) *"
        rows={5}
        className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50 resize-y"
      />
      <div className="grid grid-cols-2 gap-2">
        <input
          value={source} onChange={(e) => setSource(e.target.value)}
          placeholder="Source URL (optional)"
          className="px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50"
        />
        <input
          value={category} onChange={(e) => setCategory(e.target.value)}
          placeholder="Category (optional)"
          className="px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50"
        />
      </div>
      {error && <p className="text-xs text-red-400 flex items-center gap-1"><AlertCircle size={11} /> {error}</p>}
      <div className="flex items-center gap-2 justify-end">
        <button type="button" onClick={onCancel} className="px-3 py-1.5 text-xs text-slate-400 hover:text-white transition-colors">Cancel</button>
        <button
          type="submit"
          disabled={saving}
          className="flex items-center gap-1.5 px-4 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-60 rounded-lg text-xs text-white font-medium transition-colors"
        >
          {saving ? <><Loader2 size={11} className="animate-spin" /> Embedding…</> : <><CheckCircle2 size={11} /> Save &amp; Embed</>}
        </button>
      </div>
    </form>
  );
};

// ── Main panel ────────────────────────────────────────────────────────────────

const KnowledgePanel: React.FC<KnowledgePanelProps> = ({ isOpen, onClose }) => {
  const [chunks, setChunks] = useState<KnowledgeChunk[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<KnowledgeChunk[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [stats, setStats] = useState<{ total_chunks: number; categories: Record<string, number> } | null>(null);

  const loadChunks = useCallback(async () => {
    setLoading(true);
    try {
      const [data, statsData] = await Promise.all([
        apiFetch('?limit=100'),
        apiFetch('/stats/summary'),
      ]);
      setChunks(data ?? []);
      setStats(statsData);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) loadChunks();
  }, [isOpen, loadChunks]);

  const handleSearch = async () => {
    if (!searchQuery.trim()) { setSearchResults(null); return; }
    setSearching(true);
    try {
      const results = await apiFetch('/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery, top_k: 5, min_score: 0.4 }),
      });
      setSearchResults(results ?? []);
    } catch {
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  };

  const displayedChunks = searchResults ?? chunks;

  return (
    <>
      {/* Backdrop */}
      {isOpen && <div className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm" onClick={onClose} />}

      {/* Slide-in panel */}
      <aside
        className={`fixed top-0 right-0 h-full w-[420px] max-w-full z-50 flex flex-col
          bg-[#08101e] border-l border-white/8 shadow-2xl
          transition-transform duration-300 ease-in-out
          ${isOpen ? 'translate-x-0' : 'translate-x-full'}`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-4 border-b border-white/8">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-purple-500 to-blue-600 flex items-center justify-center shadow-lg">
              <BookOpen size={14} className="text-white" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-white">Knowledge Base</h2>
              <p className="text-xs text-slate-500">
                {stats ? `${stats.total_chunks} chunks` : 'RAG memory for M00'}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-all">
            <X size={16} />
          </button>
        </div>

        {/* Search */}
        <div className="px-4 py-3 border-b border-white/5">
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                value={searchQuery}
                onChange={(e) => { setSearchQuery(e.target.value); if (!e.target.value) setSearchResults(null); }}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="Semantic search…"
                className="w-full pl-8 pr-3 py-2 bg-white/5 border border-white/10 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/40"
              />
            </div>
            <button
              onClick={handleSearch}
              disabled={searching}
              className="px-3 py-2 bg-blue-600/80 hover:bg-blue-500 rounded-xl text-xs text-white font-medium transition-colors disabled:opacity-60 flex items-center gap-1"
            >
              {searching ? <Loader2 size={12} className="animate-spin" /> : <Search size={12} />}
            </button>
            {searchResults && (
              <button onClick={() => { setSearchResults(null); setSearchQuery(''); }} className="px-2 py-2 text-slate-400 hover:text-white">
                <X size={14} />
              </button>
            )}
          </div>
          {searchResults && (
            <p className="text-[10px] text-slate-500 mt-1.5">
              {searchResults.length} result{searchResults.length !== 1 ? 's' : ''} for "{searchQuery}"
            </p>
          )}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
          {/* Add form */}
          {showAdd && (
            <AddForm
              onAdded={(chunk) => { setChunks((p) => [chunk, ...p]); setShowAdd(false); setStats((s) => s ? { ...s, total_chunks: s.total_chunks + 1 } : null); }}
              onCancel={() => setShowAdd(false)}
            />
          )}

          {/* Loading */}
          {loading && (
            <div className="flex items-center justify-center py-12 text-slate-500">
              <Loader2 size={20} className="animate-spin mr-2" /> Loading…
            </div>
          )}

          {/* Empty */}
          {!loading && displayedChunks.length === 0 && (
            <div className="text-center py-12">
              <BookOpen size={28} className="text-slate-600 mx-auto mb-3" />
              <p className="text-sm text-slate-500">
                {searchResults ? 'No results found' : 'No knowledge chunks yet'}
              </p>
              {!searchResults && (
                <p className="text-xs text-slate-600 mt-1">Add chunks to give M00 long-term memory</p>
              )}
            </div>
          )}

          {/* Chunks */}
          {!loading && displayedChunks.map((chunk) => (
            <ChunkCard
              key={chunk.id}
              chunk={chunk}
              onDelete={(id) => { setChunks((p) => p.filter((c) => c.id !== id)); setStats((s) => s ? { ...s, total_chunks: s.total_chunks - 1 } : null); }}
            />
          ))}
        </div>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-white/5">
          <button
            onClick={() => setShowAdd((s) => !s)}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 rounded-xl text-sm text-white font-medium transition-all shadow-lg shadow-blue-500/20"
          >
            <Plus size={14} /> Add Knowledge Chunk
          </button>
        </div>
      </aside>
    </>
  );
};

export default KnowledgePanel;
