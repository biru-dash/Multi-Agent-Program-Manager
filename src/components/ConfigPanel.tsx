import { Settings, ChevronDown } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { AgentConfig } from '@/types/agent';
import { cn } from '@/lib/utils';

interface ConfigPanelProps {
  config: AgentConfig;
  onConfigChange: (config: AgentConfig) => void;
}

export const ConfigPanel = ({ config, onConfigChange }: ConfigPanelProps) => {

  return (
    <Card className="border-border bg-card/50 backdrop-blur-sm">
      <div className="p-4">
        <div className="flex items-center gap-2 mb-6">
          <Settings className="w-5 h-5 text-primary" />
          <h3 className="font-semibold text-foreground">Agent Configuration</h3>
        </div>

        <div className="space-y-6">
          {/* Model Strategy Selection */}
          <div className="space-y-2">
            <Label htmlFor="model-strategy" className="text-sm font-medium text-foreground">
              Model Strategy
            </Label>
            <Select
              value={config.modelStrategy || 'local'}
              onValueChange={(value: 'local' | 'remote' | 'hybrid') =>
                onConfigChange({ ...config, modelStrategy: value })
              }
            >
              <SelectTrigger id="model-strategy" className="bg-workflow-node-bg border-workflow-node-border">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-popover border-border">
                <SelectItem value="local">Local Models Only (Testing)</SelectItem>
                <SelectItem value="hybrid">Hybrid (API + Local Fallback)</SelectItem>
                <SelectItem value="remote">HuggingFace API Only</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Local: All models run locally. Hybrid: API for summarization, local for extraction.
            </p>
          </div>

          {/* Preprocessing Level */}
          <div className="space-y-2">
            <Label htmlFor="preprocessing" className="text-sm font-medium text-foreground">
              Preprocessing Level
            </Label>
            <Select
              value={config.preprocessing || 'advanced'}
              onValueChange={(value: 'basic' | 'advanced') =>
                onConfigChange({ ...config, preprocessing: value })
              }
            >
              <SelectTrigger id="preprocessing" className="bg-workflow-node-bg border-workflow-node-border">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-popover border-border">
                <SelectItem value="advanced">Advanced (Recommended)</SelectItem>
                <SelectItem value="basic">Basic</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Advanced includes filler removal, speaker normalization, topic segmentation
            </p>
          </div>

          {/* Confidence Threshold */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label htmlFor="confidence" className="text-sm font-medium text-foreground">
                Confidence Threshold
              </Label>
              <span className="text-sm font-mono text-primary">
                {config.confidenceThreshold}%
              </span>
            </div>
            <Slider
              id="confidence"
              value={[config.confidenceThreshold]}
              onValueChange={(value) =>
                onConfigChange({ ...config, confidenceThreshold: value[0] })
              }
              min={0}
              max={100}
              step={5}
              className="[&_[role=slider]]:bg-primary [&_[role=slider]]:border-primary"
            />
            <p className="text-xs text-muted-foreground">
              Minimum confidence level for agent outputs
            </p>
          </div>

          {/* Output Format */}
          <div className="space-y-2">
            <Label htmlFor="output-format" className="text-sm font-medium text-foreground">
              Output Format
            </Label>
            <Select
              value={config.outputFormat}
              onValueChange={(value: 'json' | 'markdown') =>
                onConfigChange({ ...config, outputFormat: value })
              }
            >
              <SelectTrigger id="output-format" className="bg-workflow-node-bg border-workflow-node-border">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-popover border-border">
                <SelectItem value="json">JSON</SelectItem>
                <SelectItem value="markdown">Markdown</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Status Summary */}
          <div className="pt-4 border-t border-border">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Config Status</span>
              <span className="text-success font-medium">Ready</span>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
};
