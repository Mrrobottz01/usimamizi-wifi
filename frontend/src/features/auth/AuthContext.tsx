import React, { createContext, useEffect, useState } from 'react';
import { User, Company } from '../../types';
import { apiFetch } from '../../lib/api-client';

interface AuthContextType {
  user: User | null;
  companies: Company[];
  selectedCompany: Company | null;
  setSelectedCompany: (company: Company) => void;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  // Synchronously restore authentication state from localStorage on page refresh
  const [user, setUser] = useState<User | null>(() => {
    try {
      const saved = localStorage.getItem('usimamizi-user');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  const [companies, setCompanies] = useState<Company[]>(() => {
    try {
      const saved = localStorage.getItem('usimamizi-companies');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const [selectedCompany, setSelectedCompany] = useState<Company | null>(() => {
    try {
      const saved = localStorage.getItem('usimamizi-active-company');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  // If there's an existing access token or user, start loading while validating in background
  const [isLoading, setIsLoading] = useState<boolean>(() => {
    return !!localStorage.getItem('usimamizi-access-token') && !localStorage.getItem('usimamizi-user');
  });

  const fetchAuthUserAndCompanies = async () => {
    const token = localStorage.getItem('usimamizi-access-token');
    const refreshToken = localStorage.getItem('usimamizi-refresh-token');

    if (!token && !refreshToken) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    try {
      // 1. Verify user profile with backend (apiFetch auto-refreshes token if expired)
      const userProfile = await apiFetch<User>('/accounts/auth/me/');
      setUser(userProfile);
      localStorage.setItem('usimamizi-user', JSON.stringify(userProfile));

      // 2. Fetch companies
      try {
        const userCompanies = await apiFetch<Company[]>('/companies/');
        setCompanies(userCompanies);
        localStorage.setItem('usimamizi-companies', JSON.stringify(userCompanies));

        if (userCompanies.length > 0) {
          const savedCompanyId = localStorage.getItem('usimamizi-active-company-id');
          const found = userCompanies.find((c) => c.id === savedCompanyId);
          const activeCompany = found || userCompanies[0];
          setSelectedCompany(activeCompany);
          localStorage.setItem('usimamizi-active-company', JSON.stringify(activeCompany));
          localStorage.setItem('usimamizi-active-company-id', activeCompany.id);
        }
      } catch (compErr) {
        console.warn('Could not refresh companies list:', compErr);
      }
    } catch (authErr) {
      console.warn('Session verification failed, logging out:', authErr);
      localStorage.removeItem('usimamizi-access-token');
      localStorage.removeItem('usimamizi-refresh-token');
      localStorage.removeItem('usimamizi-user');
      localStorage.removeItem('usimamizi-companies');
      localStorage.removeItem('usimamizi-active-company');
      localStorage.removeItem('usimamizi-active-company-id');
      setUser(null);
      setCompanies([]);
      setSelectedCompany(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAuthUserAndCompanies();
  }, []);

  const handleSetSelectedCompany = (company: Company) => {
    setSelectedCompany(company);
    localStorage.setItem('usimamizi-active-company', JSON.stringify(company));
    localStorage.setItem('usimamizi-active-company-id', company.id);
  };

  const login = async (email: string, password: string) => {
    const res = await apiFetch<{ access: string; refresh: string; user: User }>('/accounts/auth/login/', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });

    localStorage.setItem('usimamizi-access-token', res.access);
    localStorage.setItem('usimamizi-refresh-token', res.refresh);
    localStorage.setItem('usimamizi-user', JSON.stringify(res.user));
    setUser(res.user);

    try {
      const userCompanies = await apiFetch<Company[]>('/companies/');
      setCompanies(userCompanies);
      localStorage.setItem('usimamizi-companies', JSON.stringify(userCompanies));
      if (userCompanies.length > 0) {
        handleSetSelectedCompany(userCompanies[0]);
      }
    } catch (e) {
      console.warn('Could not fetch companies during login:', e);
    }
  };

  const logout = () => {
    localStorage.removeItem('usimamizi-access-token');
    localStorage.removeItem('usimamizi-refresh-token');
    localStorage.removeItem('usimamizi-user');
    localStorage.removeItem('usimamizi-companies');
    localStorage.removeItem('usimamizi-active-company');
    localStorage.removeItem('usimamizi-active-company-id');
    setUser(null);
    setCompanies([]);
    setSelectedCompany(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        companies,
        selectedCompany,
        setSelectedCompany: handleSetSelectedCompany,
        isLoading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
