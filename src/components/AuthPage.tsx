import React, { useState } from 'react';
import { ArrowRight, AtSign, Building2, Check, Eye, EyeOff, KeyRound, LockKeyhole, Mail, ShieldCheck, User } from 'lucide-react';
import './AuthPage.css';
import { useAuthStore } from '../store/authStore';

interface AuthPageProps { mode: 'login' | 'signup'; }

const GoogleMark = () => <svg viewBox="0 0 24 24" aria-hidden="true"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.27-4.74 3.27-8.1Z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.94-6.16-4.54H2.16v2.84A11 11 0 0 0 12 23Z"/><path fill="#FBBC05" d="M5.84 14.09A6.6 6.6 0 0 1 5.5 12c0-.73.13-1.43.34-2.09V7.07H2.16A11 11 0 0 0 1 12c0 1.77.42 3.44 1.16 4.93l3.68-2.84Z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.2 1.64l3.15-3.15A10.58 10.58 0 0 0 12 1a11 11 0 0 0-9.84 6.07l3.68 2.84C6.71 7.31 9.14 5.38 12 5.38Z"/></svg>;

const AuthPage: React.FC<AuthPageProps> = ({ mode }) => {
  const signup = mode === 'signup';
  const [showPassword, setShowPassword] = useState(false);
  const [role, setRole] = useState('Software Engineer');
  const [agreed, setAgreed] = useState(true);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const login = useAuthStore((state) => state.login);
  const register = useAuthStore((state) => state.signup);

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const email = String(data.get('email') ?? '');
    const password = String(data.get('password') ?? '');
    if (!email.includes('@')) return setError('Enter a valid work email.');
    if (password.length < 8) return setError('Password must contain at least 8 characters.');
    if (signup && !agreed) return setError('Please accept the Terms of Service and Privacy Policy.');
    setError('');
    setLoading(true);
    try {
      if (signup) {
        await register({ name: String(data.get('name') ?? ''), email, password, role, accepted_terms: agreed, remember: true });
      } else {
        await login({ email, password, remember: data.get('remember') === 'on' });
      }
      const next = new URLSearchParams(window.location.search).get('next');
      window.location.replace(next?.startsWith('/') && !next.startsWith('//') ? next : '/app');
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Authentication failed. Please try again.');
      setLoading(false);
    }
  };

  return <div className="auth-page">
    <div className="auth-ambient" />
    <header className="auth-nav"><a href="/" className="auth-brand"><span>M∞</span><strong>M00</strong></a><nav><a href="/">Landing</a><a href="/#architecture">Documentation</a></nav></header>
    <main className={`auth-main ${signup ? 'signup' : ''}`}>
      <section className="auth-card">
        <div className="auth-logo">M∞</div>
        <h1>{signup ? 'Start building with M00' : <>Welcome back to <em>M00</em></>}</h1>
        <p>{signup ? 'Join the next generation of engineers with autonomous AI reasoning.' : 'Sign in to access your ultra-low latency AI workspace'}</p>
        {signup && <div className="free-pill"><i /> 100 free daily queries <span>·</span> No credit card required</div>}

        <button className="oauth-button" type="button" disabled title="Google sign-in needs OAuth credentials"><GoogleMark /> Google sign-in coming soon</button>
        <div className="auth-divider"><span>{signup ? 'or register with work email' : 'or continue with work email'}</span></div>

        <form onSubmit={submit} noValidate>
          {signup && <label>Full name<div className="auth-field"><User /><input name="name" required placeholder="Ada Lovelace" autoComplete="name" /></div></label>}
          <label>Work email<div className="auth-field">{signup ? <AtSign /> : <Mail />}<input name="email" required type="email" placeholder="developer@company.com" autoComplete="email" /></div></label>
          <label><span>Password</span>{signup ? <small>Minimum 8 chars</small> : <a href="/login">Forgot password?</a>}<div className="auth-field"><LockKeyhole /><input name="password" required minLength={8} type={showPassword ? 'text' : 'password'} placeholder={signup ? 'Create a strong password (min. 8 chars)' : '••••••••••••'} autoComplete={signup ? 'new-password' : 'current-password'} /><button type="button" onClick={() => setShowPassword(!showPassword)} aria-label={showPassword ? 'Hide password' : 'Show password'}>{showPassword ? <EyeOff /> : <Eye />}</button></div></label>
          {signup && <><div className="strength"><i/><i/><i/></div><fieldset><legend>Primary role <span>(optional)</span></legend><div className="role-grid">{['Software Engineer','AI Researcher','Founder / Lead'].map(item => <button type="button" key={item} className={role === item ? 'selected' : ''} onClick={() => setRole(item)}>{role === item && <Check />}{item}</button>)}</div></fieldset><label className="check-row"><input type="checkbox" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} /><span>I agree to M00's <a href="/">Terms of Service</a> and <a href="/">Privacy Policy</a>, including Zero-Telemetry data guarantees.</span></label></>}
          {!signup && <label className="check-row remember"><input name="remember" type="checkbox" defaultChecked /><span>Remember session for 30 days</span></label>}
          {error && <div className="auth-error" role="alert">{error}</div>}
          <button className="auth-submit" type="submit" disabled={loading}>{loading ? 'Please wait…' : signup ? 'Create Free Account' : 'Sign In to M00'} {!loading && <ArrowRight />}</button>
        </form>

        {!signup && <button className="passkey-button" type="button" disabled title="Passkey and GitHub providers are not configured"><KeyRound /> Passkey / GitHub coming soon</button>}
        <p className="auth-switch">{signup ? 'Already have an account?' : "Don't have an account?"} <a href={signup ? '/login' : '/signup'}>{signup ? 'Sign in' : 'Sign up for free'} <ArrowRight /></a></p>
      </section>
      {signup ? <a className="enterprise-link" href="/#pricing"><Building2 /> Need custom VPC deployment? <strong>Contact Enterprise Sales</strong><ArrowRight /></a> : <div className="security-row"><ShieldCheck /> Protected by Zero-Telemetry Enclaves <i /> SOC2 Type II Certified</div>}
    </main>
    <footer className="auth-footer"><LockKeyhole /> Encrypted with TLS 1.3 <i /> <ShieldCheck /> Zero-Telemetry Boundary <i /> © 2026 M00 Autonomous Systems Inc.</footer>
  </div>;
};

export default AuthPage;
