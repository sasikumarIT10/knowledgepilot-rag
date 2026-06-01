'use client';

import { useState, useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Upload,
  FileText,
  Trash2,
  RefreshCw,
  Search,
  Filter,
  CheckCircle,
  XCircle,
  Clock,
  Loader2,
  X,
} from 'lucide-react';
import { api } from '@/lib/api';
import {
  cn,
  formatFileSize,
  formatDateTime,
  getFileIcon,
  getStatusColor,
  getStatusBgColor,
} from '@/lib/utils';

interface Document {
  id: string;
  original_filename: string;
  file_type: string;
  file_size: number;
  status: string;
  chunk_count: number;
  page_count: number | null;
  created_at: string;
  error_message: string | null;
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<Record<string, number>>({});
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string | null>(null);

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      const data = await api.getDocuments();
      setDocuments(data.documents);
    } catch (error) {
      console.error('Failed to load documents:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    setIsUploading(true);

    for (const file of acceptedFiles) {
      try {
        setUploadProgress((prev) => ({ ...prev, [file.name]: 0 }));
        
        await api.uploadDocument(file);
        
        setUploadProgress((prev) => ({ ...prev, [file.name]: 100 }));
      } catch (error) {
        console.error(`Failed to upload ${file.name}:`, error);
      }
    }

    setIsUploading(false);
    setUploadProgress({});
    loadDocuments();
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/markdown': ['.md'],
      'text/plain': ['.txt'],
      'text/html': ['.html'],
    },
  });

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this document?')) return;

    try {
      await api.deleteDocument(id);
      loadDocuments();
    } catch (error) {
      console.error('Failed to delete document:', error);
    }
  };

  const handleReindex = async (id: string) => {
    try {
      await api.reindexDocument(id);
      loadDocuments();
    } catch (error) {
      console.error('Failed to reindex document:', error);
    }
  };

  const filteredDocuments = documents.filter((doc) => {
    const matchesSearch = doc.original_filename
      .toLowerCase()
      .includes(searchQuery.toLowerCase());
    const matchesStatus = !statusFilter || doc.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4" />;
      case 'failed':
        return <XCircle className="w-4 h-4" />;
      case 'processing':
        return <Loader2 className="w-4 h-4 animate-spin" />;
      default:
        return <Clock className="w-4 h-4" />;
    }
  };

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold mb-2">Documents</h1>
          <p className="text-secondary">
            Upload and manage your knowledge base documents
          </p>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-secondary">
            {documents.length} document{documents.length !== 1 && 's'}
          </span>
        </div>
      </div>

      {/* Upload Zone */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <div
          {...getRootProps()}
          className={cn(
            'border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all',
            isDragActive
              ? 'border-accent bg-accent/5'
              : 'border-border hover:border-accent/50 hover:bg-muted/50'
          )}
        >
          <input {...getInputProps()} />
          <div className="flex flex-col items-center">
            <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center mb-4">
              <Upload className="w-8 h-8 text-accent" />
            </div>
            <h3 className="text-lg font-semibold mb-2">
              {isDragActive ? 'Drop files here' : 'Upload Documents'}
            </h3>
            <p className="text-secondary mb-4">
              Drag and drop files, or click to browse
            </p>
            <p className="text-xs text-secondary">
              Supported: PDF, DOCX, Markdown, TXT, HTML
            </p>
          </div>
        </div>

        {/* Upload Progress */}
        <AnimatePresence>
          {Object.keys(uploadProgress).length > 0 && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-4 space-y-2"
            >
              {Object.entries(uploadProgress).map(([filename, progress]) => (
                <div key={filename} className="glass-card p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm truncate">{filename}</span>
                    <span className="text-sm text-secondary">{progress}%</span>
                  </div>
                  <div className="h-1 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full bg-accent transition-all"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                </div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Filters */}
      <div className="flex items-center gap-4 mb-6">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-secondary" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search documents..."
            className="input-field pl-12"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-secondary" />
          {['all', 'completed', 'processing', 'pending', 'failed'].map((status) => (
            <button
              key={status}
              onClick={() => setStatusFilter(status === 'all' ? null : status)}
              className={cn(
                'px-3 py-1.5 rounded-lg text-sm transition-colors',
                (status === 'all' && !statusFilter) || statusFilter === status
                  ? 'bg-accent text-white'
                  : 'bg-muted text-secondary hover:text-white'
              )}
            >
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Documents List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-accent" />
        </div>
      ) : filteredDocuments.length === 0 ? (
        <div className="text-center py-12">
          <FileText className="w-12 h-12 text-secondary mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">No documents found</h3>
          <p className="text-secondary">
            {searchQuery || statusFilter
              ? 'Try adjusting your filters'
              : 'Upload your first document to get started'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredDocuments.map((doc, index) => (
            <motion.div
              key={doc.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="document-card"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{getFileIcon(doc.file_type)}</span>
                  <div>
                    <h3 className="font-medium truncate max-w-[180px]">
                      {doc.original_filename}
                    </h3>
                    <p className="text-xs text-secondary">
                      {formatFileSize(doc.file_size)}
                    </p>
                  </div>
                </div>
                <div
                  className={cn(
                    'flex items-center gap-1 px-2 py-1 rounded-full text-xs',
                    getStatusBgColor(doc.status),
                    getStatusColor(doc.status)
                  )}
                >
                  {getStatusIcon(doc.status)}
                  <span className="capitalize">{doc.status}</span>
                </div>
              </div>

              <div className="space-y-2 text-sm text-secondary mb-4">
                {doc.page_count && (
                  <div className="flex justify-between">
                    <span>Pages</span>
                    <span>{doc.page_count}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span>Chunks</span>
                  <span>{doc.chunk_count}</span>
                </div>
                <div className="flex justify-between">
                  <span>Uploaded</span>
                  <span>{formatDateTime(doc.created_at)}</span>
                </div>
              </div>

              {doc.error_message && (
                <div className="p-2 rounded bg-destructive/10 text-destructive text-xs mb-4">
                  {doc.error_message}
                </div>
              )}

              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleReindex(doc.id)}
                  className="flex-1 btn-ghost flex items-center justify-center gap-2 text-sm"
                >
                  <RefreshCw className="w-4 h-4" />
                  Reindex
                </button>
                <button
                  onClick={() => handleDelete(doc.id)}
                  className="p-2 rounded-lg text-destructive hover:bg-destructive/10 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
