import React, { useState, useCallback, useEffect } from 'react';
import ReactFlow, { 
  addEdge, 
  Background, 
  Controls, 
  MiniMap,
  applyEdgeChanges,
  applyNodeChanges 
} from 'reactflow';
import 'reactflow/dist/style.css';

const initialNodes = [
  { 
    id: '1', 
    data: { label: 'Audit Triggered' }, 
    position: { x: 250, y: 5 },
    style: { background: '#1e293b', color: '#f8fafc', border: '1px solid #334155' }
  },
  { 
    id: '2', 
    data: { label: 'Vision Analysis' }, 
    position: { x: 100, y: 100 },
    style: { background: '#0ea5e9', color: '#fff' }
  },
  { 
    id: '3', 
    data: { label: 'Infrastructure Check' }, 
    position: { x: 400, y: 100 },
    style: { background: '#6366f1', color: '#fff' }
  },
];

const initialEdges = [
  { id: 'e1-2', source: '1', target: '2', animated: true },
  { id: 'e1-3', source: '1', target: '3', animated: true },
];

export default function WorkflowCanvas() {
  const [nodes, setNodes] = useState(initialNodes);
  const [edges, setEdges] = useState(initialEdges);

  const onNodesChange = useCallback(
    (changes) => setNodes((nds) => applyNodeChanges(changes, nds)),
    []
  );
  const onEdgesChange = useCallback(
    (changes) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    []
  );
  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge(params, eds)),
    []
  );

  return (
    <div style={{ width: '100%', height: '500px' }} className="rounded-xl overflow-hidden border border-slate-700 shadow-2xl bg-slate-900/50 backdrop-blur-md">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        fitView
      >
        <Background color="#334155" gap={20} />
        <Controls />
        <MiniMap nodeStrokeColor={(n) => n.style.background} nodeColor="#1e293b" />
      </ReactFlow>
    </div>
  );
}
