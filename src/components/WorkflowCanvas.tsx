import { AgentState } from '@/types/agent';
import { AgentNode } from './AgentNode';
import { FileText } from 'lucide-react';
import { cn } from '@/lib/utils';

interface WorkflowCanvasProps {
  agents: AgentState[];
  workflowMode?: string; // Keep for compatibility but not used
}

export const WorkflowCanvas = ({ agents }: WorkflowCanvasProps) => {
  const miaAgent = agents.find((a) => a.id === 'mia');
  const isFlowActive = miaAgent?.status === 'processing';

  return (
    <div className="relative w-full h-full flex items-center justify-center p-8">
      {/* Background Grid */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,hsl(var(--workflow-node-border))_1px,transparent_1px),linear-gradient(to_bottom,hsl(var(--workflow-node-border))_1px,transparent_1px)] bg-[size:40px_40px] opacity-20" />

      {/* Workflow Container */}
      <div className="relative flex items-center gap-8">
        {/* Input Files */}
        <div className="w-64 p-6 rounded-xl border-2 border-dashed border-workflow-node-border bg-workflow-node-bg/50 backdrop-blur-sm animate-slide-in">
          <div className="flex items-center gap-3 mb-3">
            <FileText className="w-5 h-5 text-muted-foreground" />
            <div>
              <h3 className="font-semibold text-foreground">Transcript Files</h3>
              <p className="text-xs text-muted-foreground">Upload & Process</p>
            </div>
          </div>
          <p className="text-xs text-muted-foreground">
            Upload meeting transcripts in TXT, JSON, or SRT format
          </p>
        </div>

        {/* Connection Arrow */}
        <div className="relative flex items-center">
          <div className="w-24 h-0.5 bg-workflow-connection relative overflow-hidden">
            {isFlowActive && (
              <div className="absolute inset-0 bg-gradient-flow animate-flow" />
            )}
          </div>
          <div className={cn(
            'w-6 h-6 ml-2',
            'border-r-2 border-t-2 border-workflow-connection',
            'transform rotate-45',
            isFlowActive && 'animate-pulse-glow'
          )} />
        </div>

        {/* MIA Node */}
        {miaAgent && (
          <AgentNode 
            agent={miaAgent} 
            className="w-80 animate-slide-in [animation-delay:0.2s]"
          />
        )}
      </div>

      {/* Legend */}
      <div className="absolute bottom-4 right-4 bg-card/80 backdrop-blur-sm border border-border rounded-lg p-4">
        <p className="text-xs font-semibold text-foreground mb-2">Status Legend</p>
        <div className="space-y-1 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-agent-idle" />
            <span className="text-muted-foreground">Idle</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-agent-processing animate-pulse" />
            <span className="text-muted-foreground">Processing</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-agent-success" />
            <span className="text-muted-foreground">Success</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-agent-error" />
            <span className="text-muted-foreground">Error</span>
          </div>
        </div>
      </div>
    </div>
  );
};
