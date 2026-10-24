import React, { useEffect } from 'react';
import { useAuthStore } from '../store/authStore';

const AuthGuard: React.FC<React.PropsWithChildren> = ({ children }) => {
  const status = useAuthStore((state) => state.status);
  const checkSession = useAuthStore((state) => state.checkSession);

  useEffect(() => {
    if (status === 'idle') void checkSession();
  }, [status, checkSession]);

  useEffect(() => {
    if (status === 'anonymous') window.location.replace('/login?next=/app');
  }, [status]);

  if (status !== 'authenticated') {
    return <div className="auth-loading" role="status"><div className="loading-ring" />Checking your session…</div>;
  }
  return <>{children}</>;
};

export default AuthGuard;
