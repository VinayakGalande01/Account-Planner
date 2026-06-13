'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { useAuth } from './AuthContext';


interface DataContextType {
  accounts: any[];
  loading: boolean;
  search: string;
  setSearch: (s: string) => void;
  activeTab: string;
  setActiveTab: (tab: string) => void;
  selectedAccount: any | null;
  setSelectedAccount: (acc: any | null) => void;
  aiCommand: string | undefined;
  setAiCommand: (cmd: string | undefined) => void;
  refreshData: () => void;
}

const DataContext = createContext<DataContextType | undefined>(undefined);

export function DataProvider({ children }: { children: React.ReactNode }) {
  const { user, authFetch } = useAuth();
  const [accounts, setAccounts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [activeTab, setActiveTab] = useState('Dashboard');
  const [selectedAccount, setSelectedAccount] = useState<any | null>(null);
  const [aiCommand, setAiCommand] = useState<string | undefined>(undefined);


  const fetchData = async () => {
    if (!user) {
      setAccounts([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const res = await authFetch('/api/accounts/enriched');
      const data = await res.json();
      setAccounts(Array.isArray(data) ? data : []);
    } catch {
      try {
        const res = await authFetch('/api/accounts');
        const data = await res.json();
        setAccounts(data || []);
      } catch {
        setAccounts([]);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [user]);


  return (
    <DataContext.Provider value={{ 
      accounts, 
      loading, 
      search, 
      setSearch, 
      activeTab, 
      setActiveTab,
      selectedAccount,
      setSelectedAccount,
      aiCommand,
      setAiCommand,
      refreshData: fetchData 
    }}>
      {children}
    </DataContext.Provider>
  );
}

export function useData() {
  const context = useContext(DataContext);
  if (context === undefined) {
    throw new Error('useData must be used within a DataProvider');
  }
  return context;
}
