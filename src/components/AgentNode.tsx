import { AgentState } from '@/types/agent';
import { cn } from '@/lib/utils';
import { Brain, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { Progress } from '@/components/ui/progress';

interface AgentNodeProps {
  agent: AgentState;
  className?: string;
}

export const AgentNode = ({ agent, className }: AgentNodeProps) => {
  const getStatusIcon = () => {
    switch (agent.status) {
      case 'processing':
        return <Loader2 className="w-5 h-5 animate-spin text-agent-processing" />;
      case 'success':
        return <CheckCircle className="w-5 h-5 text-agent-success" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-agent-error" />;
      default:
        return <Brain className="w-5 h-5 text-agent-idle" />;
    }
  };

  const getStatusColor = () => {
    switch (agent.status) {
      case 'processing':
        return 'border-agent-processing shadow-[0_0_20px_hsl(var(--agent-processing)/0.3)]';
      case 'success':
        return 'border-agent-success shadow-[0_0_20px_hsl(var(--agent-success)/0.3)]';
      case 'error':
        return 'border-agent-error shadow-[0_0_20px_hsl(var(--agent-error)/0.3)]';
      default:
        return 'border-workflow-node-border';
    }
  };

  return (
    <div
      className={cn(
        'relative rounded-xl border-2 bg-workflow-node-bg backdrop-blur-sm',
        'p-6 transition-all duration-300',
        getStatusColor(),
        agent.status === 'processing' && 'animate-pulse-glow',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          {getStatusIcon()}
          <div>
            <h3 className="font-semibold text-foreground">{agent.name}</h3>
            <p className="text-xs text-muted-foreground uppercase tracking-wider">
              {agent.status}
            </p>
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      {agent.status === 'processing' && (
        <div className="space-y-2">
          <Progress value={agent.progress} className="h-2" />
          <p className="text-xs text-muted-foreground text-right">
            {agent.progress}% complete
          </p>
        </div>
      )}

      {/* Error Message */}
      {agent.status === 'error' && agent.error && (
        <div className="mt-3 p-3 rounded-lg bg-destructive/10 border border-destructive/20">
          <p className="text-xs text-destructive">{agent.error}</p>
        </div>
      )}

      {/* Success Indicator */}
      {agent.status === 'success' && (
        <div className="mt-3 p-3 rounded-lg bg-success/10 border border-success/20">
          <p className="text-xs text-success font-medium">Processing complete</p>
        </div>
      )}

      {/* Connection Points */}
      <div className="absolute -right-2 top-1/2 -translate-y-1/2 w-4 h-4 rounded-full bg-primary border-2 border-background" />
      <div className="absolute -left-2 top-1/2 -translate-y-1/2 w-4 h-4 rounded-full bg-primary border-2 border-background" />
    </div>
  );
};
