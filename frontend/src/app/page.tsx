'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';
import {
  Brain,
  Search,
  FileText,
  MessageSquare,
  Shield,
  BarChart3,
  Sparkles,
  ArrowRight,
  Check,
  Zap,
  Database,
  Network,
} from 'lucide-react';

const features = [
  {
    icon: Search,
    title: 'Semantic Search',
    description: 'Find information using natural language queries across all your documents.',
  },
  {
    icon: FileText,
    title: 'Document Intelligence',
    description: 'Extract insights from PDFs, DOCX, Markdown, and more.',
  },
  {
    icon: MessageSquare,
    title: 'Citation-Based Answers',
    description: 'Every response includes source citations for verification.',
  },
  {
    icon: Brain,
    title: 'Multi-Document Reasoning',
    description: 'Synthesize information across multiple documents.',
  },
  {
    icon: Network,
    title: 'Knowledge Graph',
    description: 'Visualize relationships between concepts and documents.',
  },
  {
    icon: Database,
    title: 'Vector Search',
    description: 'State-of-the-art embeddings for accurate retrieval.',
  },
  {
    icon: Shield,
    title: 'Enterprise Security',
    description: 'Your data stays private with secure authentication.',
  },
  {
    icon: BarChart3,
    title: 'Analytics Dashboard',
    description: 'Track usage, performance, and knowledge growth.',
  },
];

const stats = [
  { value: '99.9%', label: 'Uptime' },
  { value: '<100ms', label: 'Response Time' },
  { value: '50+', label: 'File Formats' },
  { value: '10M+', label: 'Documents Processed' },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-xl border-b border-border">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Brain className="w-8 h-8 text-accent" />
            <span className="text-xl font-bold">KnowledgePilot</span>
          </div>
          <div className="hidden md:flex items-center gap-8">
            <a href="#features" className="text-secondary hover:text-white transition-colors">Features</a>
            <a href="#how-it-works" className="text-secondary hover:text-white transition-colors">How it Works</a>
            <a href="#demo" className="text-secondary hover:text-white transition-colors">Demo</a>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/login" className="btn-ghost">Sign In</Link>
            <Link href="/register" className="btn-primary">Get Started</Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 px-6 overflow-hidden">
        {/* Animated Background */}
        <div className="absolute inset-0 animated-gradient opacity-50" />
        <div className="absolute inset-0">
          {[...Array(20)].map((_, i) => (
            <motion.div
              key={i}
              className="particle"
              style={{
                width: Math.random() * 10 + 5,
                height: Math.random() * 10 + 5,
                left: `${Math.random() * 100}%`,
                top: `${Math.random() * 100}%`,
              }}
              animate={{
                y: [0, -30, 0],
                opacity: [0.2, 0.5, 0.2],
              }}
              transition={{
                duration: Math.random() * 3 + 2,
                repeat: Infinity,
                delay: Math.random() * 2,
              }}
            />
          ))}
        </div>

        <div className="relative max-w-7xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-accent/10 border border-accent/30 mb-8">
              <Sparkles className="w-4 h-4 text-accent" />
              <span className="text-sm text-accent">Powered by Advanced RAG Technology</span>
            </div>

            <h1 className="text-5xl md:text-7xl font-bold mb-6 leading-tight">
              Your Personal AI
              <br />
              <span className="gradient-text">Knowledge Engine</span>
            </h1>

            <p className="text-xl text-secondary max-w-2xl mx-auto mb-10">
              Transform your documents into an intelligent, searchable assistant.
              Upload PDFs, notes, and documentation — get instant, accurate answers with citations.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link href="/register" className="btn-primary flex items-center gap-2 text-lg px-8 py-4">
                Get Started Free
                <ArrowRight className="w-5 h-5" />
              </Link>
              <Link href="#demo" className="btn-secondary flex items-center gap-2 text-lg px-8 py-4">
                Watch Demo
              </Link>
            </div>
          </motion.div>

          {/* Stats */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="mt-20 grid grid-cols-2 md:grid-cols-4 gap-8"
          >
            {stats.map((stat, index) => (
              <div key={index} className="text-center">
                <div className="text-4xl font-bold text-accent mb-2">{stat.value}</div>
                <div className="text-secondary">{stat.label}</div>
              </div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 px-6">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl font-bold mb-4">Powerful Features</h2>
            <p className="text-xl text-secondary max-w-2xl mx-auto">
              Everything you need to build your personal knowledge base
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                className="glass-card p-6 card-hover"
              >
                <div className="w-12 h-12 rounded-lg bg-accent/10 flex items-center justify-center mb-4">
                  <feature.icon className="w-6 h-6 text-accent" />
                </div>
                <h3 className="text-lg font-semibold mb-2">{feature.title}</h3>
                <p className="text-secondary text-sm">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="py-20 px-6 bg-card/50">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl font-bold mb-4">How It Works</h2>
            <p className="text-xl text-secondary max-w-2xl mx-auto">
              From documents to intelligent answers in seconds
            </p>
          </motion.div>

          <div className="flex flex-col md:flex-row items-center justify-center gap-8">
            {[
              { step: '1', title: 'Upload', desc: 'Drop your documents' },
              { step: '2', title: 'Process', desc: 'AI chunks & embeds' },
              { step: '3', title: 'Store', desc: 'Vector database' },
              { step: '4', title: 'Query', desc: 'Ask questions' },
              { step: '5', title: 'Answer', desc: 'Get cited responses' },
            ].map((item, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, scale: 0.8 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                className="flex flex-col items-center"
              >
                <div className="w-16 h-16 rounded-full bg-accent flex items-center justify-center text-2xl font-bold mb-4">
                  {item.step}
                </div>
                <h3 className="font-semibold mb-1">{item.title}</h3>
                <p className="text-secondary text-sm">{item.desc}</p>
                {index < 4 && (
                  <ArrowRight className="hidden md:block w-8 h-8 text-accent/50 absolute translate-x-24" />
                )}
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Demo Section */}
      <section id="demo" className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="glass-card p-8 rounded-2xl"
          >
            <div className="flex items-center gap-2 mb-6">
              <div className="w-3 h-3 rounded-full bg-destructive" />
              <div className="w-3 h-3 rounded-full bg-warning" />
              <div className="w-3 h-3 rounded-full bg-success" />
              <span className="ml-4 text-secondary text-sm">KnowledgePilot AI Chat</span>
            </div>

            <div className="space-y-4">
              <div className="chat-message-user max-w-[80%] ml-auto">
                <p>What are the key security considerations for Windows IoT deployments?</p>
              </div>

              <div className="chat-message-assistant max-w-[80%]">
                <p className="mb-3">
                  Based on your documentation, here are the key security considerations for Windows IoT deployments:
                </p>
                <ul className="list-disc list-inside space-y-2 text-secondary">
                  <li>Enable Device Guard and Credential Guard</li>
                  <li>Implement BitLocker for disk encryption</li>
                  <li>Configure Windows Firewall with strict rules</li>
                  <li>Use AppLocker for application whitelisting</li>
                </ul>
                <div className="mt-4 flex items-center gap-2">
                  <span className="source-citation">
                    📄 Windows_IoT_Security.pdf, Page 12
                  </span>
                  <span className="text-success text-sm">95% confidence</span>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-6 relative overflow-hidden">
        <div className="absolute inset-0 animated-gradient opacity-30" />
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="relative max-w-4xl mx-auto text-center"
        >
          <h2 className="text-4xl md:text-5xl font-bold mb-6">
            Turn Your Documents Into Intelligence
          </h2>
          <p className="text-xl text-secondary mb-10 max-w-2xl mx-auto">
            Join thousands of professionals who use KnowledgePilot to unlock insights from their documents.
          </p>
          <Link href="/register" className="btn-primary text-lg px-10 py-4 inline-flex items-center gap-2">
            Start Building Your Knowledge Base
            <Zap className="w-5 h-5" />
          </Link>
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-6 border-t border-border">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Brain className="w-6 h-6 text-accent" />
            <span className="font-semibold">KnowledgePilot AI</span>
          </div>
          <p className="text-secondary text-sm">
            © 2024 KnowledgePilot. Built with ❤️ for knowledge seekers.
          </p>
        </div>
      </footer>
    </div>
  );
}
