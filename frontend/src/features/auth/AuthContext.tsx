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
  const [user, setUser] = useState<User | null>(null);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchAuthUserAndCompanies = async () => {
    const token = localStorage.getItem('usimamizi-access-token');
    if (!token) {
      setIsLoading(false);
      return;
    }

    try {
      const userProfile = await apiFetch<User>('/accounts/auth/me/');
      setUser(userProfile);

      const userCompanies = await apiFetch<Company[]>('/companies/');
      setCompanies(userCompanies);
      if (userCompanies.length > 0) {
        const savedCompanyId = localStorage.getItem('usimamizi-active-company-id');
        const found = userCompanies.find((c) => c.id === savedCompanyId);
        setSelectedCompany(found || userCompanies[0]);
      }
    } catch {
      localStorage.removeItem('usimamizi-access-token');
      localStorage.removeItem('usimamizi-refresh-token');
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAuthUserAndCompanies();
  }, []);

  const handleSetSelectedCompany = (company: Company) => {
    setSelectedCompany(company);
    localStorage.setItem('usimamizi-active-company-id', company.id);
  };

  const login = async (email: string, password: string) => {
    const res = await apiFetch<{ access: string; refresh: string; user: User }>('/accounts/auth/login/', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });

    localStorage.setItem('usimamizi-access-token', res.access);
    localStorage.setItem('usimamizi-refresh-token', res.refresh);
    setUser(res.user);

    const userCompanies = await apiFetch<Company[]>('/companies/');
    setCompanies(userCompanies);
    if (userCompanies.length > 0) {
      handleSetSelectedCompany(userCompanies[0]);
    }
  };

  const logout = () => {
    localStorage.removeItem('usimamizi-access-token');
    localStorage.removeItem('usimamizi-refresh-token');
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


