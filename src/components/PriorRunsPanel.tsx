import { useState, useEffect } from 'react';
import { History, FileText, Loader2, RefreshCw, Calendar, ChevronDown, ChevronRight } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { 
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { miaService, type MIAResults } from '@/services/miaService';
import { cn } from '@/lib/utils';

interface PriorRunsPanelProps {
  onResultLoaded: (result: MIAResults, filename: string) => void;
}

interface PriorRun {
  jobId: string;
  filename: string;
  timestamp: string;
  decisions: number;
  actions: number;
  risks: number;
  status: string;
}

export const PriorRunsPanel = ({ onResultLoaded }: PriorRunsPanelProps) => {
  const [priorRuns, setPriorRuns] = useState<PriorRun[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [loadingJobId, setLoadingJobId] = useState<string | null>(null);

  const loadPriorRuns = async () => {
    setIsLoading(true);
    try {
      // Since we don't have a direct API endpoint for listing jobs,
      // we'll simulate by checking the outputs directory
      // In a real app, you'd have an endpoint like /api/jobs or /api/history
      
      // For now, we'll use a mock implementation
      // TODO: Implement backend endpoint to list prior runs
      setPriorRuns([]);
      toast.info('Prior runs feature coming soon - requires backend enhancement');
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load prior runs';
      toast.error(errorMessage);
      console.error('Error loading prior runs:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadResult = async (jobId: string, filename: string) => {
    if (loadingJobId) return;
    
    setLoadingJobId(jobId);
    try {
      const result = await miaService.getResults(jobId);
      onResultLoaded(result, filename);
      toast.success(`Loaded results from ${filename}`);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load result';
      toast.error(errorMessage);
    } finally {
      setLoadingJobId(null);
    }
  };

  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return timestamp;
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadPriorRuns();
    }
  }, [isOpen]);

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <Card className="border-border bg-card/50 backdrop-blur-sm">
        <CollapsibleTrigger className="w-full p-4 text-left hover:bg-accent/5 transition-colors">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <History className="w-5 h-5 text-primary" />
              <h3 className="font-semibold text-foreground">Prior Runs</h3>
              {priorRuns.length > 0 && (
                <Badge variant="secondary" className="ml-2">
                  {priorRuns.length}
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-2">
              {isLoading && <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />}
              {isOpen ? (
                <ChevronDown className="w-4 h-4 text-muted-foreground" />
              ) : (
                <ChevronRight className="w-4 h-4 text-muted-foreground" />
              )}
            </div>
          </div>
        </CollapsibleTrigger>
        
        <CollapsibleContent>
          <div className="px-4 pb-4">
            <div className="flex items-center justify-between mb-4">
              <p className="text-sm text-muted-foreground">
                Load results from previous processing runs
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={loadPriorRuns}
                disabled={isLoading}
                className="gap-2"
              >
                <RefreshCw className={cn("w-4 h-4", isLoading && "animate-spin")} />
                Refresh
              </Button>
            </div>

            {priorRuns.length === 0 && !isLoading ? (
              <div className="text-center py-8 text-muted-foreground">
                <History className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p className="font-medium mb-1">No prior runs found</p>
                <p className="text-sm">
                  Process some transcripts to see them here
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {priorRuns.map((run) => (
                  <Card key={run.jobId} className="p-3 bg-accent/5 border-border/50">
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <FileText className="w-4 h-4 text-primary flex-shrink-0" />
                          <h4 className="font-medium text-sm truncate">
                            {run.filename}
                          </h4>
                          <Badge 
                            variant={run.status === 'completed' ? 'default' : 'secondary'}
                            className="text-xs"
                          >
                            {run.status}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-4 text-xs text-muted-foreground mb-2">
                          <div className="flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            <span>{formatTimestamp(run.timestamp)}</span>
                          </div>
                        </div>
                        <div className="flex items-center gap-4 text-xs">
                          <span className="text-success">{run.decisions} decisions</span>
                          <span className="text-accent">{run.actions} actions</span>
                          <span className="text-warning">{run.risks} risks</span>
                        </div>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => loadResult(run.jobId, run.filename)}
                        disabled={loadingJobId === run.jobId}
                        className="ml-3 text-xs"
                      >
                        {loadingJobId === run.jobId ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : (
                          'Load'
                        )}
                      </Button>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  );
};