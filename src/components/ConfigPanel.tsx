import { Settings, ChevronDown, Zap, Brain, Sliders } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { AgentConfig } from '@/types/agent';
import { cn } from '@/lib/utils';

interface ConfigPanelProps {
  config: AgentConfig;
  onConfigChange: (config: AgentConfig) => void;
}

export const ConfigPanel = ({ config, onConfigChange }: ConfigPanelProps) => {
  const isOllama = config.modelStrategy === 'ollama';

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
              onValueChange={(value: 'local' | 'remote' | 'hybrid' | 'ollama') =>
                onConfigChange({ ...config, modelStrategy: value })
              }
            >
              <SelectTrigger id="model-strategy" className="bg-workflow-node-bg border-workflow-node-border">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-popover border-border">
                <SelectItem value="ollama">🚀 Ollama (Llama 3) - Enhanced Quality</SelectItem>
                <SelectItem value="hybrid">Hybrid (API + Local Fallback)</SelectItem>
                <SelectItem value="local">Local Models Only (Testing)</SelectItem>
                <SelectItem value="remote">HuggingFace API Only</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Ollama: Best quality with Llama 3 for structured extraction. Hybrid: API + local fallback.
            </p>
            {isOllama && (
              <div className="mt-2 p-2 bg-primary/10 rounded-md border border-primary/20">
                <p className="text-xs text-primary font-medium">🚀 Ollama Mode Active - Advanced parameters available below</p>
              </div>
            )}
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

          {/* Advanced Ollama Parameters */}
          {isOllama && (
            <div className="space-y-4 pt-2 border border-primary/20 rounded-md p-4 bg-primary/5">
              <div className="flex items-center gap-2 mb-4">
                <Zap className="w-4 h-4 text-primary" />
                <h4 className="font-medium text-foreground">Advanced Ollama Parameters</h4>
              </div>
                {/* Temperature */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Label className="text-sm font-medium text-foreground">
                      Temperature
                    </Label>
                    <span className="text-sm font-mono text-primary">
                      {(config.temperature ?? 0.3).toFixed(1)}
                    </span>
                  </div>
                  <Slider
                    value={[config.temperature ?? 0.3]}
                    onValueChange={(value) =>
                      onConfigChange({ ...config, temperature: value[0] })
                    }
                    min={0}
                    max={1}
                    step={0.1}
                    className="[&_[role=slider]]:bg-primary [&_[role=slider]]:border-primary"
                  />
                  <p className="text-xs text-muted-foreground">
                    0.0 = Deterministic, 1.0 = Very Creative. 0.2-0.4 recommended for extraction.
                  </p>
                </div>

                {/* Max Tokens */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Label className="text-sm font-medium text-foreground">
                      Max Tokens
                    </Label>
                    <span className="text-sm font-mono text-primary">
                      {config.maxTokens ?? 2000}
                    </span>
                  </div>
                  <Slider
                    value={[config.maxTokens ?? 2000]}
                    onValueChange={(value) =>
                      onConfigChange({ ...config, maxTokens: value[0] })
                    }
                    min={500}
                    max={4000}
                    step={100}
                    className="[&_[role=slider]]:bg-primary [&_[role=slider]]:border-primary"
                  />
                  <p className="text-xs text-muted-foreground">
                    Maximum response length. Higher = more comprehensive results.
                  </p>
                </div>

                {/* Top P */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Label className="text-sm font-medium text-foreground">
                      Top P (Nucleus Sampling)
                    </Label>
                    <span className="text-sm font-mono text-primary">
                      {(config.topP ?? 0.9).toFixed(1)}
                    </span>
                  </div>
                  <Slider
                    value={[config.topP ?? 0.9]}
                    onValueChange={(value) =>
                      onConfigChange({ ...config, topP: value[0] })
                    }
                    min={0.1}
                    max={1.0}
                    step={0.1}
                    className="[&_[role=slider]]:bg-primary [&_[role=slider]]:border-primary"
                  />
                  <p className="text-xs text-muted-foreground">
                    Controls vocabulary diversity. 0.9 = balanced, 1.0 = full vocabulary.
                  </p>
                </div>

                {/* Extraction Mode */}
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-foreground">
                    Extraction Mode
                  </Label>
                  <Select
                    value={config.extractionMode ?? 'comprehensive'}
                    onValueChange={(value: 'comprehensive' | 'focused' | 'creative') =>
                      onConfigChange({ ...config, extractionMode: value })
                    }
                  >
                    <SelectTrigger className="bg-workflow-node-bg border-workflow-node-border">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-popover border-border">
                      <SelectItem value="comprehensive">🎯 Comprehensive (Most thorough)</SelectItem>
                      <SelectItem value="focused">⚡ Focused (Faster, key items)</SelectItem>
                      <SelectItem value="creative">🧠 Creative (Finds subtle patterns)</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    Comprehensive: Maximum extraction. Focused: Key items only. Creative: Finds implicit risks.
                  </p>
                </div>

                {/* Context Chunking */}
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <Label className="text-sm font-medium text-foreground">
                      Context Chunking
                    </Label>
                    <p className="text-xs text-muted-foreground">
                      Split long transcripts for better coverage
                    </p>
                  </div>
                  <Switch
                    checked={config.contextChunking ?? false}
                    onCheckedChange={(checked) =>
                      onConfigChange({ ...config, contextChunking: checked })
                    }
                  />
                </div>

                {/* Chunk Size (only if chunking enabled) */}
                {config.contextChunking && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <Label className="text-sm font-medium text-foreground">
                        Chunk Size
                      </Label>
                      <span className="text-sm font-mono text-primary">
                        {config.chunkSize ?? 8000} chars
                      </span>
                    </div>
                    <Slider
                      value={[config.chunkSize ?? 8000]}
                      onValueChange={(value) =>
                        onConfigChange({ ...config, chunkSize: value[0] })
                      }
                      min={4000}
                      max={15000}
                      step={1000}
                      className="[&_[role=slider]]:bg-primary [&_[role=slider]]:border-primary"
                    />
                    <p className="text-xs text-muted-foreground">
                      Size of each processing chunk. Larger = more context per chunk.
                    </p>
                  </div>
                )}
            </div>
          )}

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
