'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
  BarChart3,
  TrendingUp,
  FileText,
  MessageSquare,
  Calendar,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import { api } from '@/lib/api';

interface DailyStats {
  date: string;
  queries: number;
  documents_uploaded: number;
  tokens_used: number;
}

interface TopTopic {
  topic: string;
  count: number;
  percentage: number;
}

interface Analytics {
  summary: {
    total_documents: number;
    total_chunks: number;
    total_queries: number;
    total_tokens_used: number;
    avg_confidence_score: number;
    documents_this_week: number;
    queries_this_week: number;
  };
  daily_stats: DailyStats[];
  top_topics: TopTopic[];
  recent_queries?: string[];
}

export default function AnalyticsPage() {
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const data = await api.getAnalytics();
        setAnalytics(data);
      } catch (err) {
        console.error('Failed to fetch analytics:', err);
        setError('Failed to load analytics. Please refresh the page.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchAnalytics();
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-accent" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 flex flex-col items-center justify-center min-h-[60vh] text-center">
        <AlertCircle className="w-12 h-12 text-destructive mb-4" />
        <h2 className="text-xl font-semibold mb-2">Analytics unavailable</h2>
        <p className="text-secondary">{error}</p>
      </div>
    );
  }

  const dailyStats = analytics?.daily_stats ?? [];
  const topTopics = analytics?.top_topics ?? [];

  const maxDailyQueries = Math.max(
    ...dailyStats.map((d) => d.queries),
    1
  );

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Analytics</h1>
        <p className="text-secondary">
          Track your knowledge base usage and performance
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {[
          {
            label: 'Total Documents',
            value: analytics?.summary.total_documents || 0,
            icon: FileText,
            change: analytics?.summary.documents_this_week || 0,
          },
          {
            label: 'Total Queries',
            value: analytics?.summary.total_queries || 0,
            icon: MessageSquare,
            change: analytics?.summary.queries_this_week || 0,
          },
          {
            label: 'Avg Confidence',
            value: `${((analytics?.summary.avg_confidence_score || 0) * 100).toFixed(1)}%`,
            icon: TrendingUp,
          },
          {
            label: 'Total Chunks',
            value: analytics?.summary.total_chunks || 0,
            icon: BarChart3,
          },
        ].map((stat, index) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className="stats-card"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 rounded-lg bg-accent/10">
                <stat.icon className="w-6 h-6 text-accent" />
              </div>
              {stat.change !== undefined && (
                <span className="text-sm text-success">+{stat.change} this week</span>
              )}
            </div>
            <div className="text-3xl font-bold mb-1">
              {typeof stat.value === 'number' ? stat.value.toLocaleString() : stat.value}
            </div>
            <div className="text-secondary text-sm">{stat.label}</div>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Daily Usage Chart */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="glass-card p-6"
        >
          <div className="flex items-center gap-2 mb-6">
            <Calendar className="w-5 h-5 text-accent" />
            <h2 className="text-xl font-semibold">Daily Activity</h2>
          </div>

          <div className="space-y-4">
            {dailyStats.slice(-7).map((day, index) => (
              <div key={day.date} className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-secondary">
                    {new Date(day.date).toLocaleDateString('en-US', {
                      weekday: 'short',
                      month: 'short',
                      day: 'numeric',
                    })}
                  </span>
                  <span>
                    {day.queries} queries · {day.documents_uploaded} uploads
                  </span>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{
                      width: `${(day.queries / maxDailyQueries) * 100}%`,
                    }}
                    transition={{ duration: 0.5, delay: index * 0.1 }}
                    className="h-full bg-accent rounded-full"
                  />
                </div>
              </div>
            ))}

            {dailyStats.length === 0 && (
              <div className="text-center py-8 text-secondary">
                No activity data yet
              </div>
            )}
          </div>
        </motion.div>

        {/* Top Topics */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="glass-card p-6"
        >
          <div className="flex items-center gap-2 mb-6">
            <TrendingUp className="w-5 h-5 text-accent" />
            <h2 className="text-xl font-semibold">Top Topics</h2>
          </div>

          <div className="space-y-4">
            {topTopics.map((topic, index) => (
              <div key={topic.topic} className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="font-medium">{topic.topic}</span>
                  <span className="text-secondary">{topic.count} documents</span>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${topic.percentage}%` }}
                    transition={{ duration: 0.5, delay: index * 0.1 }}
                    className="h-full bg-gradient-to-r from-accent to-purple-500 rounded-full"
                  />
                </div>
              </div>
            ))}

            {topTopics.length === 0 && (
              <div className="text-center py-8 text-secondary">
                No topic data yet
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </div>
  );
}
