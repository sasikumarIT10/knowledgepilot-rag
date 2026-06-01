'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Send,
  Loader2,
  Plus,
  MessageSquare,
  Trash2,
  FileText,
  ChevronDown,
  Sparkles,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { api } from '@/lib/api';
import { useChatStore } from '@/lib/store';
import { cn, getConfidenceColor, getConfidenceLabel } from '@/lib/utils';

interface Source {
  document_id: string;
  document_name: string;
  chunk_id: string;
  content: string;
  page_number: number | null;
  relevance_score: number;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  confidence_score?: number;
  created_at: string;
}

export default function ChatPage() {
  const [input, setInput] = useState('');
  const [expandedSources, setExpandedSources] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const {
    currentSessionId,
    sessions,
    messages,
    isLoading,
    setCurrentSession,
    setSessions,
    setMessages,
    addMessage,
    setLoading,
    clearChat,
  } = useChatStore();

  useEffect(() => {
    loadSessions();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadSessions = async () => {
    try {
      const data = await api.getChatSessions();
      setSessions(data.sessions);
    } catch (error) {
      console.error('Failed to load sessions:', error);
    }
  };

  const loadSession = async (sessionId: string) => {
    try {
      const data = await api.getChatHistory(sessionId);
      setCurrentSession(sessionId);
      setMessages(data.messages);
    } catch (error) {
      console.error('Failed to load session:', error);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      created_at: new Date().toISOString(),
    };

    addMessage(userMessage);
    setInput('');
    setLoading(true);

    try {
      const response = await api.sendMessage(input.trim(), currentSessionId || undefined, {
        include_sources: true,
        max_sources: 5,
      });

      const assistantMessage: Message = {
        id: response.message_id,
        role: 'assistant',
        content: response.content,
        sources: response.sources,
        confidence_score: response.confidence_score,
        created_at: response.created_at,
      };

      addMessage(assistantMessage);

      if (!currentSessionId) {
        setCurrentSession(response.session_id);
        loadSessions();
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      addMessage({
        id: Date.now().toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        created_at: new Date().toISOString(),
      });
    } finally {
      setLoading(false);
    }
  };

  const handleNewChat = () => {
    clearChat();
  };

  const handleDeleteSession = async (sessionId: string) => {
    try {
      await api.deleteChatSession(sessionId);
      if (currentSessionId === sessionId) {
        clearChat();
      }
      loadSessions();
    } catch (error) {
      console.error('Failed to delete session:', error);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="h-screen flex">
      {/* Sessions Sidebar */}
      <div className="w-64 border-r border-border flex flex-col bg-card/50">
        <div className="p-4 border-b border-border">
          <button
            onClick={handleNewChat}
            className="btn-primary w-full flex items-center justify-center gap-2"
          >
            <Plus className="w-4 h-4" />
            New Chat
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {sessions.map((session) => (
            <div
              key={session.id}
              className={cn(
                'group flex items-center gap-2 p-3 rounded-lg cursor-pointer transition-colors',
                currentSessionId === session.id
                  ? 'bg-accent/10 text-accent'
                  : 'hover:bg-muted'
              )}
              onClick={() => loadSession(session.id)}
            >
              <MessageSquare className="w-4 h-4 flex-shrink-0" />
              <span className="flex-1 truncate text-sm">{session.title}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDeleteSession(session.id);
                }}
                className="opacity-0 group-hover:opacity-100 p-1 hover:bg-destructive/20 rounded transition-all"
              >
                <Trash2 className="w-3 h-3 text-destructive" />
              </button>
            </div>
          ))}

          {sessions.length === 0 && (
            <div className="text-center text-secondary text-sm py-8">
              No conversations yet
            </div>
          )}
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center">
              <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center mb-4">
                <Sparkles className="w-8 h-8 text-accent" />
              </div>
              <h2 className="text-2xl font-bold mb-2">Ask Your Knowledge Base</h2>
              <p className="text-secondary max-w-md">
                Ask questions about your uploaded documents. I&apos;ll provide answers
                with citations from your knowledge base.
              </p>
            </div>
          ) : (
            <AnimatePresence>
              {messages.map((message) => (
                <motion.div
                  key={message.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={cn(
                    'max-w-3xl',
                    message.role === 'user' ? 'ml-auto' : 'mr-auto'
                  )}
                >
                  <div
                    className={cn(
                      message.role === 'user'
                        ? 'chat-message-user'
                        : 'chat-message-assistant'
                    )}
                  >
                    {message.role === 'assistant' ? (
                      <div className="markdown-content">
                        <ReactMarkdown>{message.content}</ReactMarkdown>
                      </div>
                    ) : (
                      <p>{message.content}</p>
                    )}

                    {/* Sources */}
                    {message.sources && message.sources.length > 0 && (
                      <div className="mt-4 pt-4 border-t border-border">
                        <button
                          onClick={() =>
                            setExpandedSources(
                              expandedSources === message.id ? null : message.id
                            )
                          }
                          className="flex items-center gap-2 text-sm text-secondary hover:text-white transition-colors"
                        >
                          <FileText className="w-4 h-4" />
                          <span>{message.sources.length} sources</span>
                          <ChevronDown
                            className={cn(
                              'w-4 h-4 transition-transform',
                              expandedSources === message.id && 'rotate-180'
                            )}
                          />
                        </button>

                        <AnimatePresence>
                          {expandedSources === message.id && (
                            <motion.div
                              initial={{ height: 0, opacity: 0 }}
                              animate={{ height: 'auto', opacity: 1 }}
                              exit={{ height: 0, opacity: 0 }}
                              className="overflow-hidden"
                            >
                              <div className="mt-3 space-y-2">
                                {message.sources.map((source, idx) => (
                                  <div
                                    key={idx}
                                    className="p-3 rounded-lg bg-muted text-sm"
                                  >
                                    <div className="flex items-center justify-between mb-2">
                                      <span className="font-medium">
                                        {source.document_name}
                                      </span>
                                      <span className="text-xs text-secondary">
                                        {source.page_number && `Page ${source.page_number}`}
                                      </span>
                                    </div>
                                    <p className="text-secondary line-clamp-3">
                                      {source.content}
                                    </p>
                                    <div className="mt-2 text-xs text-accent">
                                      {(source.relevance_score * 100).toFixed(0)}% relevant
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                    )}

                    {/* Confidence Score */}
                    {message.confidence_score !== undefined && (
                      <div className="mt-3 flex items-center gap-2 text-sm">
                        <span className="text-secondary">Confidence:</span>
                        <span
                          className={cn(
                            'font-medium',
                            getConfidenceColor(message.confidence_score)
                          )}
                        >
                          {getConfidenceLabel(message.confidence_score)} (
                          {(message.confidence_score * 100).toFixed(0)}%)
                        </span>
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          )}

          {isLoading && (
            <div className="flex items-center gap-2 text-secondary">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Thinking...</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-4 border-t border-border">
          <form onSubmit={handleSubmit} className="max-w-3xl mx-auto">
            <div className="relative">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a question about your documents..."
                rows={1}
                className="input-field pr-12 resize-none min-h-[52px] max-h-32"
                style={{ height: 'auto' }}
              />
              <button
                type="submit"
                disabled={!input.trim() || isLoading}
                className={cn(
                  'absolute right-3 top-1/2 -translate-y-1/2 p-2 rounded-lg transition-colors',
                  input.trim() && !isLoading
                    ? 'bg-accent text-white hover:bg-accent/90'
                    : 'bg-muted text-secondary'
                )}
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
            <p className="text-xs text-secondary text-center mt-2">
              Answers are generated from your uploaded documents only
            </p>
          </form>
        </div>
      </div>
    </div>
  );
}
