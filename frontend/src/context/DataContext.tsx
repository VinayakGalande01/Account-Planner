'use client';

/**
 * CRM DATA CONTEXT PROVIDER (DataContext.tsx)
 * Global CRM data store managing enriched account records, active search queries,
 * active tab navigation states, account selection, and automatic retry data fetching.
 */

// --- SECTION 1: Dependencies & Data Context Schema ---
// Imports React hooks, AuthContext integration, and defines DataContextType schema.
import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
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

// --- SECTION 2: Data Provider State & Fetch Handlers ---
// Executes async REST API fetches for enriched account records with fallback retries.
const DataContext = createContext<DataContextType | undefined>(undefined);

export function DataProvider({ children }: { children: React.ReactNode }) {
  const { user, authFetch, loading: authLoading } = useAuth();
  const [accounts, setAccounts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [activeTab, setActiveTab] = useState('Dashboard');
  const [selectedAccount, setSelectedAccount] = useState<any | null>(null);
  const [aiCommand, setAiCommand] = useState<string | undefined>(undefined);

  const latestRequestId = useRef(0);

  const fetchData = async () => {
    if (authLoading) return;
    
    if (!user) {
      setAccounts([]);
      setLoading(false);
      return;
    }
    
    latestRequestId.current += 1;
    const myRequestId = latestRequestId.current;
    
    setLoading(true);

    const fetchWithRetry = async (url: string): Promise<Response> => {
      try {
        const res = await authFetch(url);
        if (!res.ok) throw new Error(`Fetch failed: ${res.status}`);
        return res;
      } catch (err) {
        console.warn(`[RETRY] Initial request for ${url} failed. Retrying in 1s...`, err);
        await new Promise(resolve => setTimeout(resolve, 1000));
        const res = await authFetch(url);
        if (!res.ok) throw new Error(`Retry failed: ${res.status}`);
        return res;
      }
    };
    
    try {
      const res = await fetchWithRetry('/api/accounts/enriched');
      const data = await res.json();
      
      if (myRequestId === latestRequestId.current) {
        setAccounts(Array.isArray(data) ? data : []);
      }
    } catch {
      try {
        const res = await fetchWithRetry('/api/accounts');
        const data = await res.json();
        
        if (myRequestId === latestRequestId.current) {
          setAccounts(data || []);
        }
      } catch {
        if (myRequestId === latestRequestId.current) {
          setAccounts([]);
        }
      }
    } finally {
      if (myRequestId === latestRequestId.current) {
        setLoading(false);
      }
    }
  };

  useEffect(() => {
    if (!authLoading) {
      fetchData();
    }
  }, [user?.id, authLoading]);


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
