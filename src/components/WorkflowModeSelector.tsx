import { WorkflowMode } from '@/types/agent';
import { Card } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { GitBranch, Zap } from 'lucide-react';

interface WorkflowModeSelectorProps {
  mode: WorkflowMode;
  onModeChange: (mode: WorkflowMode) => void;
}

export const WorkflowModeSelector = ({ mode, onModeChange }: WorkflowModeSelectorProps) => {
  return (
    <Card className="p-4 border-border bg-card/50 backdrop-blur-sm">
      <Label className="text-sm font-semibold text-foreground mb-3 block">
        Workflow Mode
      </Label>
      <RadioGroup value={mode} onValueChange={(value) => onModeChange(value as WorkflowMode)}>
        <div className="space-y-3">
          <div className="flex items-start space-x-3 p-3 rounded-lg border border-border hover:border-primary/50 transition-colors">
            <RadioGroupItem value="full-pipeline" id="full-pipeline" className="mt-0.5" />
            <div className="flex-1">
              <Label htmlFor="full-pipeline" className="flex items-center gap-2 font-medium cursor-pointer">
                <GitBranch className="w-4 h-4 text-primary" />
                Full Pipeline (MIA → REA)
              </Label>
              <p className="text-xs text-muted-foreground mt-1">
                Process transcripts through MIA first, then extract requirements via REA
              </p>
            </div>
          </div>
          
          <div className="flex items-start space-x-3 p-3 rounded-lg border border-border hover:border-secondary/50 transition-colors">
            <RadioGroupItem value="direct-rea" id="direct-rea" className="mt-0.5" />
            <div className="flex-1">
              <Label htmlFor="direct-rea" className="flex items-center gap-2 font-medium cursor-pointer">
                <Zap className="w-4 h-4 text-secondary" />
                Direct REA
              </Label>
              <p className="text-xs text-muted-foreground mt-1">
                Skip MIA and extract requirements directly from files
              </p>
            </div>
          </div>
        </div>
      </RadioGroup>
    </Card>
  );
};
