import React from 'react';
import {
  ArrowRight, BrainCircuit, Check, ChevronRight, Code2, Database,
  FileSearch, Globe2, Layers3, Menu, Search, ShieldCheck, Sparkles,
  TerminalSquare, X, Zap,
} from 'lucide-react';
import './LandingPage.css';

const capabilities = [
  { icon: Globe2, eyebrow: 'Grounded intelligence', title: 'Real-time web research', text: 'Search, compare, and synthesize live sources into clear answers with citations you can inspect.', wide: true },
  { icon: BrainCircuit, eyebrow: 'Reasoning architecture', title: 'Deep neural reasoning', text: 'Complex questions get deliberate, multi-step analysis powered by NVIDIA Nemotron.' },
  { icon: FileSearch, eyebrow: 'Document intelligence', title: 'Multi-modal context', text: 'Bring files, pages, images, and internal knowledge into a single focused conversation.' },
  { icon: ShieldCheck, eyebrow: 'Private by design', title: 'Zero-telemetry control', text: 'Keep your knowledge layer controlled, auditable, and separate from the interface.', wide: true },
];

const plans = [
  { name: 'Developer', price: '$0', desc: 'For exploring M00 and personal projects.', items: ['Core M00 reasoning model', 'Web research', 'Saved conversations', 'Community support'], action: 'Start building' },
  { name: 'Pro Architect', price: '$20', desc: 'For builders who need deeper context.', items: ['Everything in Developer', 'Advanced reasoning modes', 'Knowledge base tools', 'Priority inference'], action: 'Upgrade to Pro', featured: true },
  { name: 'Enterprise Hub', price: 'Custom', desc: 'For teams deploying intelligence at scale.', items: ['Private deployment', 'Custom integrations', 'Team workspaces', 'Dedicated support'], action: 'Contact us' },
];

const LandingPage: React.FC = () => {
  const [mobileNav, setMobileNav] = React.useState(false);
  return <div className="landing">
    <header className="landing-nav">
      <a className="landing-brand" href="#top"><span>M∞</span><strong>M00</strong></a>
      <nav className={mobileNav ? 'open' : ''}>
        <a href="#features" onClick={() => setMobileNav(false)}>Features</a>
        <a href="#performance" onClick={() => setMobileNav(false)}>Benchmarks</a>
        <a href="#architecture" onClick={() => setMobileNav(false)}>Architecture</a>
        <a href="#pricing" onClick={() => setMobileNav(false)}>Pricing</a>
      </nav>
      <div className="nav-actions"><a className="nav-signin" href="/login">Sign in</a><a className="nav-launch" href="/signup">Launch M00 <ArrowRight size={14} /></a></div>
      <button className="mobile-menu" onClick={() => setMobileNav(!mobileNav)} aria-label="Toggle navigation">{mobileNav ? <X /> : <Menu />}</button>
    </header>

    <main id="top">
      <section className="landing-hero">
        <div className="hero-grid" />
        <div className="hero-orb one" /><div className="hero-orb two" />
        <div className="release-pill"><Sparkles size={13} /> M00 2.0 is live <ChevronRight size={13} /></div>
        <p className="hero-kicker">Intelligence infrastructure for ambitious builders</p>
        <h1>Think deeper.<br /><span>Build beyond.</span></h1>
        <p className="hero-copy">M00 is the AI workspace that turns complex questions into researched, reasoned, and actionable answers—without losing your flow.</p>
        <div className="hero-actions"><a className="primary-cta" href="/app"><Zap size={17} /> Try M00 now</a><a className="secondary-cta" href="#features"><TerminalSquare size={17} /> Explore the system</a></div>
        <div className="hero-proof"><span><i /> Live web intelligence</span><span><i /> NVIDIA-powered reasoning</span><span><i /> Your context, remembered</span></div>
      </section>

      <section className="product-stage" aria-label="M00 product preview">
        <div className="stage-glow" />
        <div className="product-window">
          <div className="window-bar"><div><span /><span /><span /></div><p>app.m00.ai / workspace</p><small>System online</small></div>
          <div className="product-body">
            <aside className="preview-sidebar">
              <div className="preview-brand"><span>M∞</span> M00</div>
              <button><span>+</span> New research</button>
              <small>Recent threads</small>
              <a className="active">Neural search architecture</a><a>Agent memory patterns</a><a>RAG performance review</a>
              <div className="preview-usage"><span>Context window</span><strong>82%</strong><div><i /></div></div>
            </aside>
            <div className="preview-main">
              <div className="preview-question">Compare the strongest retrieval architectures for a production research agent.</div>
              <div className="preview-search"><Search size={15} /><span>Research complete</span><em>12 sources analyzed</em><small>Live web</small></div>
              <div className="preview-answer">
                <div className="ai-mini"><BrainCircuit size={18} /></div>
                <div><p className="answer-label">M00 · Deep reasoning</p><h3>Hybrid retrieval wins when accuracy and latency matter.</h3><p>A production system should combine semantic retrieval with a lightweight reranker, then reserve generation context for the highest-signal evidence.</p>
                  <div className="code-preview"><div><span>architecture.ts</span><button>Copy</button></div><code><b>const</b> context = <i>await</i> retrieve(query);<br/><b>const</b> evidence = rerank(context);<br/><b>return</b> synthesize(evidence);</code></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="trusted-strip"><p>Powered by focused, production-grade intelligence</p><div><span><BrainCircuit /> Neural reasoning</span><span><Globe2 /> Live sources</span><span><Database /> MongoDB context</span><span><Layers3 /> Retrieval augmented</span></div></section>

      <section className="landing-section capabilities" id="features">
        <div className="section-heading"><span>System capabilities</span><h2>Engineered for clarity<br />and cognitive depth</h2><p>Every layer is designed to help you move from uncertainty to a confident next step.</p></div>
        <div className="capability-grid">{capabilities.map(({ icon: Icon, eyebrow, title, text, wide }) => <article key={title} className={wide ? 'wide' : ''}><div className="feature-icon"><Icon /></div><small>{eyebrow}</small><h3>{title}</h3><p>{text}</p><a href="/app">Explore capability <ArrowRight size={14} /></a></article>)}</div>
      </section>

      <section className="landing-section performance" id="performance">
        <div className="section-heading"><span>Measured performance</span><h2>Fast enough for flow.<br />Deep enough for the hard parts.</h2></div>
        <div className="metrics"><div><strong>1M</strong><span>token context</span></div><div><strong>3B</strong><span>active parameters</span></div><div><strong>6</strong><span>integrated tools</span></div><div><strong>24/7</strong><span>research workspace</span></div></div>
        <div className="benchmark-card"><div className="benchmark-copy"><span>Adaptive intelligence</span><h3>One workspace.<br/>Every mode of thinking.</h3><p>M00 routes each request through the right combination of search, retrieval, tools, and reasoning—automatically.</p><ul><li><Check /> Live-information detection</li><li><Check /> Source-grounded synthesis</li><li><Check /> Long-context memory</li></ul></div><div className="benchmark-bars"><div><span>Research synthesis</span><i style={{'--score':'94%'} as React.CSSProperties}/><b>94</b></div><div><span>Context retention</span><i style={{'--score':'89%'} as React.CSSProperties}/><b>89</b></div><div><span>Tool selection</span><i style={{'--score':'97%'} as React.CSSProperties}/><b>97</b></div><div><span>Code reasoning</span><i style={{'--score':'92%'} as React.CSSProperties}/><b>92</b></div></div></div>
      </section>

      <section className="landing-section architecture" id="architecture"><div className="architecture-copy"><span>Developer first</span><h2>A capable system,<br/>without the complexity.</h2><p>Streaming responses, persistent conversations, retrieval, web research, and rich outputs are already wired together.</p><ul><li><Code2 /> React + TypeScript interface</li><li><TerminalSquare /> FastAPI streaming backend</li><li><Database /> MongoDB knowledge and history</li></ul><a className="text-link" href="/app">Open the workspace <ArrowRight /></a></div><div className="terminal-card"><div><span>m00_client.py</span><small>Python</small></div><pre><em>from</em> openai <em>import</em> OpenAI{`\n\n`}client = OpenAI({`\n`}  base_url=<b>"http://localhost:8000"</b>{`\n`}){`\n\n`}response = client.chat.completions.create({`\n`}  model=<b>"m00"</b>,{`\n`}  messages=[{`{`}<b>"role"</b>: <b>"user"</b>, ...{`}`}] {`\n`})</pre></div></section>

      <section className="landing-section pricing" id="pricing"><div className="section-heading"><span>Simple pricing</span><h2>Scale with your ambition</h2><p>Start free. Move up when deeper reasoning and shared knowledge become essential.</p></div><div className="pricing-grid">{plans.map((plan) => <article key={plan.name} className={plan.featured ? 'featured' : ''}>{plan.featured && <label>Most popular</label>}<span>{plan.name}</span><h3>{plan.price}{plan.price.startsWith('$') && <small>/month</small>}</h3><p>{plan.desc}</p><ul>{plan.items.map(item => <li key={item}><Check />{item}</li>)}</ul><a href="/app">{plan.action}</a></article>)}</div></section>

      <section className="final-cta"><div className="cta-icon"><Sparkles /></div><h2>Your next breakthrough<br/>starts with a better question.</h2><p>Step into a workspace built for deep thought and decisive execution.</p><a href="/app">Launch M00 <ArrowRight /></a><small>No setup required · Start building immediately</small></section>
    </main>

    <footer className="landing-footer"><div><a className="landing-brand" href="#top"><span>M∞</span><strong>M00</strong></a><p>Intelligence, amplified.</p></div><div><strong>Product</strong><a href="#features">Features</a><a href="#performance">Benchmarks</a><a href="#pricing">Pricing</a></div><div><strong>Resources</strong><a href="/app">Workspace</a><a href="#architecture">Architecture</a><a href="#top">Documentation</a></div><div><strong>Company</strong><a href="#top">About</a><a href="#top">Privacy</a><a href="#top">Contact</a></div><small>© 2026 M00. Built for builders.</small></footer>
  </div>;
};

export default LandingPage;
