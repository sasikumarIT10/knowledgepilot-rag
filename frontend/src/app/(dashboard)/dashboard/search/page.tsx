'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Search, FileText, Loader2, Sparkles } from 'lucide-react';
import { api } from '@/lib/api';
import { cn, getConfidenceColor } from '@/lib/utils';

interface SearchResult {
  document_id: string;
  document_name: string;
  chunk_id: string;
  content: string;
  page_number: number | null;
  relevance_score: number;
}

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchType, setSearchType] = useState<'semantic' | 'hybrid'>('semantic');

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setIsLoading(true);
    try {
      const data = searchType === 'semantic'
        ? await api.search(query)
        : await api.hybridSearch(query);
      setResults(data.results);
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Search</h1>
        <p className="text-secondary">
          Search across your knowledge base using natural language
        </p>
      </div>

      {/* Search Form */}
      <form onSubmit={handleSearch} className="mb-8">
        <div className="flex gap-4 mb-4">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-secondary" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask a question or search for information..."
              className="input-field pl-12 text-lg"
            />
          </div>
          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className="btn-primary px-8"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              'Search'
            )}
          </button>
        </div>

        <div className="flex items-center gap-4">
          <span className="text-sm text-secondary">Search type:</span>
          {(['semantic', 'hybrid'] as const).map((type) => (
            <button
              key={type}
              type="button"
              onClick={() => setSearchType(type)}
              className={cn(
                'px-4 py-2 rounded-lg text-sm transition-colors',
                searchType === type
                  ? 'bg-accent text-white'
                  : 'bg-muted text-secondary hover:text-white'
              )}
            >
              {type.charAt(0).toUpperCase() + type.slice(1)}
            </button>
          ))}
        </div>
      </form>

      {/* Results */}
      {results.length > 0 ? (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">
              {results.length} result{results.length !== 1 && 's'}
            </h2>
          </div>

          {results.map((result, index) => (
            <motion.div
              key={result.chunk_id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="glass-card p-6"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <FileText className="w-5 h-5 text-accent" />
                  <div>
                    <h3 className="font-medium">{result.document_name}</h3>
                    {result.page_number && (
                      <span className="text-xs text-secondary">
                        Page {result.page_number}
                      </span>
                    )}
                  </div>
                </div>
                <div
                  className={cn(
                    'text-sm font-medium',
                    getConfidenceColor(result.relevance_score)
                  )}
                >
                  {(result.relevance_score * 100).toFixed(0)}% match
                </div>
              </div>
              <p className="text-secondary">{result.content}</p>
            </motion.div>
          ))}
        </div>
      ) : !isLoading && query ? (
        <div className="text-center py-12">
          <Search className="w-12 h-12 text-secondary mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">No results found</h3>
          <p className="text-secondary">
            Try adjusting your search query or upload more documents
          </p>
        </div>
      ) : (
        <div className="text-center py-12">
          <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center mx-auto mb-4">
            <Sparkles className="w-8 h-8 text-accent" />
          </div>
          <h3 className="text-lg font-semibold mb-2">Semantic Search</h3>
          <p className="text-secondary max-w-md mx-auto">
            Search your documents using natural language. Our AI understands
            context and meaning, not just keywords.
          </p>
        </div>
      )}
    </div>
  );
}
