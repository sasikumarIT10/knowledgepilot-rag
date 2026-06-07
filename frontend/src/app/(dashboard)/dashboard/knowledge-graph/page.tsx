'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  MarkerType,
  type Edge,
  type Node,
  type NodeProps,
} from 'reactflow';
import 'reactflow/dist/style.css';
import {
  FileText,
  Loader2,
  Network,
  RefreshCw,
  Tag,
} from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

interface GraphNodeData {
  label: string;
  nodeType: string;
  size: number;
  metadata?: Record<string, unknown> | null;
}

interface KnowledgeGraphNode {
  id: string;
  label: string;
  type: string;
  size: number;
  metadata?: Record<string, unknown> | null;
}

interface KnowledgeGraphEdge {
  source: string;
  target: string;
  weight: number;
  relationship: string;
}

interface KnowledgeGraph {
  nodes: KnowledgeGraphNode[];
  edges: KnowledgeGraphEdge[];
}

function DocumentNode({ data, selected }: NodeProps<GraphNodeData>) {
  return (
    <div
      className={cn(
        'px-4 py-3 rounded-xl border min-w-[160px] max-w-[220px] shadow-lg transition-all',
        'bg-card/95 border-accent/40',
        selected && 'ring-2 ring-accent border-accent'
      )}
    >
      <div className="flex items-start gap-2">
        <FileText className="w-4 h-4 text-accent flex-shrink-0 mt-0.5" />
        <div className="min-w-0">
          <p className="text-sm font-medium truncate" title={data.label}>
            {data.label}
          </p>
          <p className="text-xs text-secondary mt-1">
            {data.metadata?.file_type
              ? String(data.metadata.file_type).toUpperCase()
              : 'Document'}
            {data.metadata?.chunks != null && ` · ${data.metadata.chunks} chunks`}
          </p>
        </div>
      </div>
    </div>
  );
}

function TopicNode({ data, selected }: NodeProps<GraphNodeData>) {
  return (
    <div
      className={cn(
        'px-5 py-3 rounded-full border min-w-[100px] text-center shadow-lg transition-all',
        'bg-gradient-to-br from-purple-500/20 to-accent/20 border-purple-400/50',
        selected && 'ring-2 ring-purple-400'
      )}
    >
      <div className="flex items-center justify-center gap-2">
        <Tag className="w-4 h-4 text-purple-300" />
        <span className="text-sm font-semibold">{data.label}</span>
      </div>
      <p className="text-xs text-secondary mt-1">{data.size} links</p>
    </div>
  );
}

const nodeTypes = {
  document: DocumentNode,
  topic: TopicNode,
};

function layoutGraph(graph: KnowledgeGraph): { nodes: Node<GraphNodeData>[]; edges: Edge[] } {
  const topics = graph.nodes.filter((n) => n.type === 'topic');
  const documents = graph.nodes.filter((n) => n.type === 'document');

  const topicIndex = new Map(topics.map((t, i) => [t.id, i]));

  const flowNodes: Node<GraphNodeData>[] = [];

  topics.forEach((node, index) => {
    flowNodes.push({
      id: node.id,
      type: 'topic',
      position: { x: index * 280 + 80, y: 40 },
      data: {
        label: node.label,
        nodeType: node.type,
        size: node.size,
        metadata: node.metadata,
      },
    });
  });

  const docsByTopic = new Map<number, KnowledgeGraphNode[]>();
  documents.forEach((doc) => {
    const edge = graph.edges.find(
      (e) => e.source === doc.id && e.relationship === 'belongs_to'
    );
    const idx = edge ? (topicIndex.get(edge.target) ?? 0) : 0;
    if (!docsByTopic.has(idx)) docsByTopic.set(idx, []);
    docsByTopic.get(idx)!.push(doc);
  });

  documents.forEach((node) => {
    const edge = graph.edges.find(
      (e) => e.source === node.id && e.relationship === 'belongs_to'
    );
    const topicIdx = edge ? (topicIndex.get(edge.target) ?? 0) : 0;
    const columnDocs = docsByTopic.get(topicIdx) ?? [];
    const rowIdx = columnDocs.findIndex((d) => d.id === node.id);

    flowNodes.push({
      id: node.id,
      type: 'document',
      position: {
        x: topicIdx * 280 + 40,
        y: 160 + rowIdx * 130,
      },
      data: {
        label: node.label,
        nodeType: node.type,
        size: node.size,
        metadata: node.metadata,
      },
    });
  });

  const flowEdges: Edge[] = graph.edges.map((edge, index) => ({
    id: `${edge.source}-${edge.target}-${index}`,
    source: edge.source,
    target: edge.target,
    label: edge.relationship.replace('_', ' '),
    animated: edge.relationship === 'belongs_to',
    style: {
      stroke:
        edge.relationship === 'belongs_to'
          ? 'hsl(217 91% 60%)'
          : 'hsl(270 60% 60%)',
      strokeWidth: Math.max(1, edge.weight * 2),
    },
    labelStyle: { fill: 'hsl(240 5% 65%)', fontSize: 10 },
    markerEnd: {
      type: MarkerType.ArrowClosed,
      color:
        edge.relationship === 'belongs_to'
          ? 'hsl(217 91% 60%)'
          : 'hsl(270 60% 60%)',
    },
  }));

  return { nodes: flowNodes, edges: flowEdges };
}

export default function KnowledgeGraphPage() {
  const [graph, setGraph] = useState<KnowledgeGraph | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNodeData | null>(null);

  const loadGraph = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.getKnowledgeGraph();
      setGraph(data);
    } catch (err) {
      console.error('Failed to load knowledge graph:', err);
      setError('Failed to load knowledge graph. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  const { nodes, edges } = useMemo(
    () => (graph ? layoutGraph(graph) : { nodes: [], edges: [] }),
    [graph]
  );

  const documentCount = graph?.nodes.filter((n) => n.type === 'document').length ?? 0;
  const topicCount = graph?.nodes.filter((n) => n.type === 'topic').length ?? 0;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-accent" />
      </div>
    );
  }

  return (
    <div className="p-8 h-screen flex flex-col">
      <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold mb-2 flex items-center gap-3">
            <Network className="w-8 h-8 text-accent" />
            Knowledge Graph
          </h1>
          <p className="text-secondary">
            Visualize how your documents connect by type and similarity
          </p>
        </div>
        <button
          onClick={loadGraph}
          className="btn-secondary flex items-center gap-2 self-start"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        {[
          { label: 'Documents', value: documentCount },
          { label: 'Topics', value: topicCount },
          { label: 'Connections', value: graph?.edges.length ?? 0 },
        ].map((stat, index) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.08 }}
            className="stats-card"
          >
            <div className="text-2xl font-bold">{stat.value}</div>
            <div className="text-secondary text-sm">{stat.label}</div>
          </motion.div>
        ))}
      </div>

      {error && (
        <div className="mb-4 p-4 rounded-lg bg-destructive/10 text-destructive border border-destructive/20">
          {error}
        </div>
      )}

      <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-6">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="glass-card overflow-hidden min-h-[480px] h-full"
        >
          {documentCount === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-8">
              <Network className="w-16 h-16 text-muted mb-4" />
              <h2 className="text-xl font-semibold mb-2">No graph data yet</h2>
              <p className="text-secondary max-w-md">
                Upload and process documents to see them appear as nodes connected
                by file type and similarity.
              </p>
            </div>
          ) : (
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={nodeTypes}
              fitView
              fitViewOptions={{ padding: 0.2 }}
              onNodeClick={(_, node) => setSelectedNode(node.data)}
              onPaneClick={() => setSelectedNode(null)}
              proOptions={{ hideAttribution: true }}
            >
              <Background color="hsl(240 4% 16%)" gap={20} />
              <Controls className="!bg-card !border-border !shadow-lg" />
              <MiniMap
                className="!bg-card !border-border"
                nodeColor={(node) =>
                  node.type === 'topic' ? 'hsl(270 60% 60%)' : 'hsl(217 91% 60%)'
                }
                maskColor="hsl(0 0% 4% / 0.75)"
              />
            </ReactFlow>
          )}
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: 12 }}
          animate={{ opacity: 1, x: 0 }}
          className="glass-card p-6 h-fit lg:sticky lg:top-8"
        >
          <h2 className="text-lg font-semibold mb-4">Legend</h2>
          <div className="space-y-3 text-sm mb-6">
            <div className="flex items-center gap-3">
              <div className="w-4 h-4 rounded-full bg-accent/60" />
              <span>Document node</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-4 h-4 rounded-full bg-purple-500/60" />
              <span>File type topic</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-8 h-0.5 bg-accent" />
              <span>belongs to type</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-8 h-0.5 bg-purple-500" />
              <span>similar type link</span>
            </div>
          </div>

          <h2 className="text-lg font-semibold mb-3">Selection</h2>
          {selectedNode ? (
            <div className="space-y-2 text-sm">
              <p className="font-medium break-words">{selectedNode.label}</p>
              <p className="text-secondary capitalize">{selectedNode.nodeType}</p>
              {selectedNode.metadata && (
                <dl className="mt-3 space-y-1 text-secondary">
                  {Object.entries(selectedNode.metadata).map(([key, value]) => (
                    <div key={key} className="flex justify-between gap-2">
                      <dt className="capitalize">{key.replace('_', ' ')}</dt>
                      <dd className="text-foreground text-right truncate max-w-[140px]">
                        {String(value)}
                      </dd>
                    </div>
                  ))}
                </dl>
              )}
            </div>
          ) : (
            <p className="text-secondary text-sm">
              Click a node to inspect document or topic details.
            </p>
          )}
        </motion.div>
      </div>
    </div>
  );
}
