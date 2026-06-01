'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
  FileText,
  MessageSquare,
  Database,
  Zap,
  TrendingUp,
  TrendingDown,
  Upload,
  ArrowRight,
} from 'lucide-react';
import Link from 'next/link';
import { api } from '@/lib/api';

interface AnalyticsSummary {
  total_documents: number;
  total_chunks: number;
  total_queries: number;
  total_tokens_used: number;
  avg_confidence_score: number;
  documents_this_week: number;
  queries_this_week: number;
}

export default function DashboardPage() {
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const data = await api.getAnalytics();
        setAnalytics(data.summary);
      } catch (error) {
        console.error('Failed to fetch analytics:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchAnalytics();
  }, []);

  const stats = [
    {
      label: 'Total Documents',
      value: analytics?.total_documents || 0,
      icon: FileText,
      color: 'text-accent',
      bgColor: 'bg-accent/10',
      change: analytics?.documents_this_week || 0,
      changeLabel: 'this week',
    },
    {
      label: 'Total Chunks',
      value: analytics?.total_chunks || 0,
      icon: Database,
      color: 'text-success',
      bgColor: 'bg-success/10',
    },
    {
      label: 'Queries Made',
      value: analytics?.total_queries || 0,
      icon: MessageSquare,
      color: 'text-warning',
      bgColor: 'bg-warning/10',
      change: analytics?.queries_this_week || 0,
      changeLabel: 'this week',
    },
    {
      label: 'Tokens Used',
      value: analytics?.total_tokens_used || 0,
      icon: Zap,
      color: 'text-purple-500',
      bgColor: 'bg-purple-500/10',
    },
  ];

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Dashboard</h1>
        <p className="text-secondary">Welcome to your knowledge base overview</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {stats.map((stat, index) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className="stats-card"
          >
            <div className="flex items-center justify-between mb-4">
              <div className={`p-3 rounded-lg ${stat.bgColor}`}>
                <stat.icon className={`w-6 h-6 ${stat.color}`} />
              </div>
              {stat.change !== undefined && (
                <div className="flex items-center gap-1 text-sm">
                  <TrendingUp className="w-4 h-4 text-success" />
                  <span className="text-success">+{stat.change}</span>
                </div>
              )}
            </div>
            <div className="text-3xl font-bold mb-1">
              {isLoading ? (
                <div className="skeleton h-8 w-20" />
              ) : (
                stat.value.toLocaleString()
              )}
            </div>
            <div className="text-secondary text-sm">{stat.label}</div>
            {stat.changeLabel && (
              <div className="text-xs text-secondary mt-1">{stat.changeLabel}</div>
            )}
          </motion.div>
        ))}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="glass-card p-6"
        >
          <h2 className="text-xl font-semibold mb-4">Quick Actions</h2>
          <div className="space-y-3">
            <Link
              href="/dashboard/documents"
              className="flex items-center justify-between p-4 rounded-lg bg-muted hover:bg-muted/80 transition-colors"
            >
              <div className="flex items-center gap-3">
                <Upload className="w-5 h-5 text-accent" />
                <span>Upload Documents</span>
              </div>
              <ArrowRight className="w-5 h-5 text-secondary" />
            </Link>
            <Link
              href="/dashboard/chat"
              className="flex items-center justify-between p-4 rounded-lg bg-muted hover:bg-muted/80 transition-colors"
            >
              <div className="flex items-center gap-3">
                <MessageSquare className="w-5 h-5 text-accent" />
                <span>Start New Chat</span>
              </div>
              <ArrowRight className="w-5 h-5 text-secondary" />
            </Link>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="glass-card p-6"
        >
          <h2 className="text-xl font-semibold mb-4">Performance</h2>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-secondary">Avg. Confidence Score</span>
                <span className="font-medium">
                  {isLoading ? (
                    <span className="skeleton h-4 w-12 inline-block" />
                  ) : (
                    `${((analytics?.avg_confidence_score || 0) * 100).toFixed(1)}%`
                  )}
                </span>
              </div>
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${(analytics?.avg_confidence_score || 0) * 100}%` }}
                  transition={{ duration: 1, delay: 0.5 }}
                  className="h-full bg-accent rounded-full"
                />
              </div>
            </div>
            <div className="pt-4 border-t border-border">
              <div className="flex items-center justify-between">
                <span className="text-secondary text-sm">Knowledge Coverage</span>
                <span className="text-success text-sm font-medium">Good</span>
              </div>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Getting Started */}
      {analytics?.total_documents === 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="glass-card p-8 text-center"
        >
          <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center mx-auto mb-4">
            <Upload className="w-8 h-8 text-accent" />
          </div>
          <h2 className="text-2xl font-bold mb-2">Get Started</h2>
          <p className="text-secondary mb-6 max-w-md mx-auto">
            Upload your first document to start building your personal knowledge base.
            Support for PDF, DOCX, Markdown, and more.
          </p>
          <Link href="/dashboard/documents" className="btn-primary inline-flex items-center gap-2">
            Upload Your First Document
            <ArrowRight className="w-5 h-5" />
          </Link>
        </motion.div>
      )}
    </div>
  );
}
