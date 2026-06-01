import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Providers } from '@/components/providers';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'KnowledgePilot AI - Enterprise Personal Knowledge Base',
  description: 'Transform your documents into an intelligent searchable assistant powered by RAG technology.',
  keywords: ['AI', 'RAG', 'Knowledge Base', 'Document Intelligence', 'LLM'],
  authors: [{ name: 'KnowledgePilot Team' }],
  openGraph: {
    title: 'KnowledgePilot AI',
    description: 'Your Personal AI Knowledge Engine',
    type: 'website',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-background text-foreground antialiased`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
