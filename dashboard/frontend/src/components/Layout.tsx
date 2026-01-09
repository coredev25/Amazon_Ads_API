'use client';

import React, { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  LayoutDashboard,
  Target,
  Key,
  Lightbulb,
  BookOpen,
  Ban,
  History,
  Settings,
  Menu,
  X,
  ChevronRight,
  Zap,
  LogOut,
  User,
  Search as SearchIcon,
  Moon,
  Sun,
} from 'lucide-react';
import { cn } from '@/utils/helpers';
import { useAuth } from '@/contexts/AuthContext';
import MultiAccountSwitcher from './MultiAccountSwitcher';
import { fetchAccounts } from '@/utils/api';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useTheme } from '@/contexts/ThemeContext';
import { search, SearchResult } from '@/utils/api';

interface LayoutProps {
  children: React.ReactNode;
}

const navItems = [
  { href: '/dashboard', icon: LayoutDashboard, label: 'Command Center' },
  { href: '/dashboard/campaigns-v2', icon: Target, label: 'Campaign Manager' },
  { href: '/dashboard/keywords', icon: Key, label: 'Keywords & Targeting' },
  { href: '/dashboard/recommendations', icon: Lightbulb, label: 'AI Recommendations' },
  { href: '/dashboard/ai-control', icon: Zap, label: 'AI Control' },
  { href: '/dashboard/rules', icon: BookOpen, label: 'Rule Engine' },
  { href: '/dashboard/negatives', icon: Ban, label: 'Negative Keywords' },
  { href: '/dashboard/changelog', icon: History, label: 'Transparency Log' },
  { href: '/dashboard/change-history', icon: History, label: 'Change History' },
  { href: '/dashboard/settings', icon: Settings, label: 'Strategy Config' },
];

export default function Layout({ children }: LayoutProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const queryClient = useQueryClient();
  const [currentAccountId, setCurrentAccountId] = useState<string | undefined>();

  // Fetch accounts for multi-account switcher
  const { data: accounts } = useQuery({
    queryKey: ['accounts'],
    queryFn: fetchAccounts,
    enabled: true,
  });

  const handleAccountChange = (accountId: string) => {
    setCurrentAccountId(accountId);
    // Store in localStorage for persistence
    localStorage.setItem('current_account_id', accountId);
    // Invalidate all queries to refetch with new account
    // queryClient.invalidateQueries();
  };

  // Load saved account on mount
  useEffect(() => {
    const savedAccountId = localStorage.getItem('current_account_id');
    if (savedAccountId && accounts?.some(a => a.account_id === savedAccountId)) {
      setCurrentAccountId(savedAccountId);
    } else if (accounts && accounts.length > 0) {
      setCurrentAccountId(accounts[0].account_id);
    }
  }, [accounts]);

  // Handle responsive behavior
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 768) {
        setSidebarOpen(true);
        setMobileMenuOpen(false);
      } else {
        setSidebarOpen(false);
        setMobileMenuOpen(false);
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Toggle sidebar (mobile and desktop)
  const toggleSidebar = () => {
    if (window.innerWidth < 768) {
      setMobileMenuOpen(!mobileMenuOpen);
    } else {
      setSidebarOpen(!sidebarOpen);
    }
  };
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [showSearchResults, setShowSearchResults] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const searchRef = useRef<HTMLDivElement>(null);

  // Handle search input with debounce
  useEffect(() => {
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    if (searchQuery.trim().length === 0) {
      setSearchResults([]);
      setShowSearchResults(false);
      return;
    }

    if (searchQuery.trim().length < 2) {
      return;
    }

    setIsSearching(true);
    searchTimeoutRef.current = setTimeout(async () => {
      try {
        const response = await search(searchQuery.trim(), 10);
        setSearchResults(response.results);
        setShowSearchResults(response.results.length > 0);
      } catch (error) {
        console.error('Search error:', error);
        setSearchResults([]);
        setShowSearchResults(false);
      } finally {
        setIsSearching(false);
      }
    }, 300);

    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, [searchQuery]);

  // Close search results when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setShowSearchResults(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleSearchResultClick = (result: SearchResult) => {
    setShowSearchResults(false);
    setSearchQuery('');

    if (result.type === 'campaign') {
      router.push(`/dashboard/campaigns?campaign_id=${result.id}`);
    } else if (result.type === 'keyword') {
      router.push(`/dashboard/keywords?keyword_id=${result.id}`);
    } else if (result.type === 'ad_group') {
      router.push(`/dashboard/campaigns?ad_group_id=${result.id}`);
    }
  };

  const getResultIcon = (type: string) => {
    switch (type) {
      case 'campaign':
        return Target;
      case 'keyword':
        return Key;
      case 'ad_group':
        return LayoutDashboard;
      default:
        return SearchIcon;
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Mobile Overlay */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 md:hidden"
          onClick={() => {
            setSidebarOpen(false);
            setMobileMenuOpen(false);
          }}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed left-0 top-0 z-40 h-screen transition-all duration-300',
          'bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 shadow-lg',
          sidebarOpen ? 'w-64' : 'w-20',
          // Mobile: show when mobileMenuOpen, hidden otherwise
          'md:block',
          mobileMenuOpen ? 'block' : 'hidden md:block'
        )}
      >
        {/* Logo */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-gray-200 dark:border-gray-700">
          {sidebarOpen && (
            <Link href="/dashboard" className="flex items-center gap-3" onClick={() => setMobileMenuOpen(false)}>
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-amazon-orange to-amazon-orange-dark flex items-center justify-center">
                <Zap className="w-6 h-6 text-black" />
              </div>
              <div className="animate-fade-in">
                <div className="font-bold text-gray-900 dark:text-white text-sm">Amazon PPC</div>
                <div className="text-xs text-gray-500 dark:text-gray-400">AI Dashboard</div>
              </div>
            </Link>
          )}
          {/* Toggle Button */}
          <div className="h-16 flex items-center justify-end px-4 border-b border-gray-200 dark:border-gray-700">
            <button
              onClick={toggleSidebar}
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              aria-label="Toggle sidebar"
            >
              {(sidebarOpen || mobileMenuOpen) ? (
                <X className="w-5 h-5 text-gray-600 dark:text-gray-400" />
              ) : (
                <Menu className="w-5 h-5 text-gray-600 dark:text-gray-400" />
              )}
            </button>
          </div>
        </div>

        {/* Navigation */}
        <nav className="p-4 space-y-2">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;

            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className={cn(
                  'nav-item',
                  isActive && 'active',
                  !sidebarOpen && 'justify-center px-3'
                )}
                title={!sidebarOpen ? item.label : undefined}
              >
                <Icon className="w-5 h-5 flex-shrink-0" />
                {sidebarOpen && (
                  <span className="animate-fade-in">{item.label}</span>
                )}
                {sidebarOpen && isActive && (
                  <ChevronRight className="w-4 h-4 ml-auto text-amazon-orange" />
                )}
              </Link>
            );
          })}
        </nav>

      </aside>

      {/* Main Content */}
      <main
        className={cn(
          'flex-1 flex flex-col min-h-screen transition-all duration-300 overflow-hidden',
          sidebarOpen ? 'md:ml-64' : 'md:ml-20'
        )}
      >
        {/* Top Bar */}
        <header className="h-16 flex-shrink-0 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 sticky top-0 z-30">
          <div className="h-full px-4 md:px-6 flex items-center justify-between max-w-full">
            {/* Mobile Menu Button */}
            <button
              onClick={toggleSidebar}
              className="md:hidden p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors mr-2"
            >
              <Menu className="w-5 h-5 text-gray-600 dark:text-gray-400" />
            </button>

            <div className="flex items-center gap-4 flex-1">
              <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
                {navItems.find((item) => item.href === pathname)?.label || 'Dashboard'}
              </h1>
            </div>
            <div className="flex items-center gap-2 md:gap-4">
              {/* Search */}
              <div className="relative" ref={searchRef}>
                <div className="relative">
                  <input
                    type="text"
                    placeholder="Search campaigns, keywords..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onFocus={() => {
                      if (searchResults.length > 0) {
                        setShowSearchResults(true);
                      }
                    }}
                    className="input w-40 md:w-64 lg:w-72 pl-10 pr-10 py-2 text-sm"
                  />
                  <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 dark:text-gray-500" />
                  {isSearching && (
                    <div className="absolute right-3 top-1/2 -translate-y-1/2">
                      <div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
                    </div>
                  )}
                </div>

                {/* Search Results Dropdown */}
                {showSearchResults && searchResults.length > 0 && (
                  <div className="absolute top-full left-0 right-0 mt-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-xl z-50 max-h-96 overflow-y-auto">
                    <div className="p-2">
                      {searchResults.map((result) => {
                        const Icon = getResultIcon(result.type);
                        return (
                          <button
                            key={`${result.type}-${result.id}`}
                            onClick={() => handleSearchResultClick(result)}
                            className="w-full text-left p-3 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors group"
                          >
                            <div className="flex items-start gap-3">
                              <Icon className="w-4 h-4 text-gray-400 dark:text-gray-500 mt-0.5 flex-shrink-0 group-hover:text-amazon-orange transition-colors" />
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                  <span className="text-sm font-medium text-gray-900 dark:text-white truncate">
                                    {result.name}
                                  </span>
                                  <span className="text-xs px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 capitalize">
                                    {result.type.replace('_', ' ')}
                                  </span>
                                </div>
                                {result.campaign_name && (
                                  <div className="text-xs text-gray-500 dark:text-gray-400 mt-1 truncate">
                                    Campaign: {result.campaign_name}
                                    {result.ad_group_name && ` • Ad Group: ${result.ad_group_name}`}
                                  </div>
                                )}
                              </div>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}

                {showSearchResults && searchResults.length === 0 && searchQuery.trim().length >= 2 && !isSearching && (
                  <div className="absolute top-full left-0 right-0 mt-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-xl z-50 p-4">
                    <p className="text-sm text-gray-500 dark:text-gray-400 text-center">No results found</p>
                  </div>
                )}
              </div>

              {/* Multi-Account Switcher */}
              {accounts && accounts.length > 1 && (
                <MultiAccountSwitcher
                  accounts={accounts}
                  currentAccountId={currentAccountId}
                  onAccountChange={handleAccountChange}
                />
              )}

              {/* Theme Toggle */}
              <button
                onClick={toggleTheme}
                className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                title={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
              >
                {theme === 'light' ? (
                  <Moon className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                ) : (
                  <Sun className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                )}
              </button>

              {/* User Menu */}
              <div className="flex items-center gap-2 md:gap-3 md:pl-4 md:border-l md:border-gray-200 dark:md:border-gray-700">
                <div className="text-right hidden md:block">
                  <div className="text-sm font-medium text-gray-900 dark:text-white">{user?.username}</div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">{user?.role}</div>
                </div>
                <button
                  onClick={logout}
                  className="p-2 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors group"
                  title="Logout"
                >
                  <LogOut className="w-5 h-5 text-gray-600 dark:text-gray-400 group-hover:text-red-600" />
                </button>
              </div>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <div className="flex-1 p-4 md:p-6 overflow-auto">
          <div className="max-w-full">{children}</div>
        </div>
      </main>
    </div>
  );
}

