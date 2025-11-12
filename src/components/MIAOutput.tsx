import React, { useState, useMemo } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { FileText, CheckSquare, AlertTriangle, Users, Download, ArrowUpDown, Clock, Target } from 'lucide-react';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { type MIAResults } from '@/services/miaService';
import { toast } from 'sonner';
import { ProvenanceView } from './ProvenanceView';
import { EnhancedDecisionCard } from './EnhancedDecisionCard';

interface MIAOutputProps {
  output: MIAResults | null;
  processedTranscriptFilename?: string | null;
}

const getConfidenceBadge = (confidence: number) => {
  if (confidence >= 0.8) return { label: 'High', variant: 'default' as const, color: 'text-green-500' };
  if (confidence >= 0.6) return { label: 'Medium', variant: 'secondary' as const, color: 'text-yellow-500' };
  return { label: 'Low', variant: 'outline' as const, color: 'text-red-500' };
};

const downloadJSON = (data: any, filename: string) => {
  const jsonStr = JSON.stringify(data, null, 2);
  const blob = new Blob([jsonStr], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${filename}.json`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
  toast.success(`Downloaded ${filename}.json`);
};

type SortOption = 'timestamp' | 'confidence';

export const MIAOutput = ({ output, processedTranscriptFilename }: MIAOutputProps) => {
  const [sortBy, setSortBy] = useState<SortOption>('timestamp');

  // Function to parse timestamp for sorting
  const parseTimestamp = (timestamp?: string): number => {
    if (!timestamp) return 0;
    
    // Handle formats like "14:23", "1:23:45", etc.
    const parts = timestamp.split(':').map(p => parseInt(p, 10));
    if (parts.length === 2) {
      return parts[0] * 60 + parts[1]; // minutes * 60 + seconds
    } else if (parts.length === 3) {
      return parts[0] * 3600 + parts[1] * 60 + parts[2]; // hours * 3600 + minutes * 60 + seconds
    }
    return 0;
  };

  // Function to get attribution timestamp for a decision
  const getDecisionTimestamp = (decision: any): string => {
    // Try to get timestamp from provenance first
    if (decision.provenance?.source_segment_ids && output?.metadata?.original_segments) {
      const sourceSegment = output.metadata.original_segments[decision.provenance.source_segment_ids[0]];
      if (sourceSegment?.timestamp) {
        return sourceSegment.timestamp;
      }
    }
    
    // Fallback to decision's direct timestamp
    return decision.timestamp || '00:00';
  };

  // Sorted decisions with memoization for performance
  const sortedDecisions = useMemo(() => {
    if (!output?.decisions) return [];
    
    const decisionsWithTimestamps = output.decisions.map(decision => ({
      ...decision,
      calculatedTimestamp: getDecisionTimestamp(decision)
    }));

    return [...decisionsWithTimestamps].sort((a, b) => {
      if (sortBy === 'timestamp') {
        // Sort by timestamp (chronological order)
        const timeA = parseTimestamp(a.calculatedTimestamp);
        const timeB = parseTimestamp(b.calculatedTimestamp);
        return timeA - timeB;
      } else {
        // Sort by confidence (highest first)
        return (b.confidence || 0) - (a.confidence || 0);
      }
    });
  }, [output?.decisions, output?.metadata?.original_segments, sortBy]);

  if (!output) {
    return (
      <Card className="p-8 text-center border-border bg-card/50">
        <FileText className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
        <p className="text-muted-foreground">
          Upload a transcript to see MIA analysis
        </p>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with Transcript Info and Download All Button */}
      <div className="flex items-center justify-between mb-4">
        {processedTranscriptFilename ? (
          <div className="flex items-center gap-2 text-sm">
            <FileText className="w-4 h-4 text-muted-foreground" />
            <span className="text-muted-foreground">Source:</span>
            <span className="font-medium text-foreground">{processedTranscriptFilename}</span>
          </div>
        ) : (
          <div />
        )}
        <Button
          variant="default"
          size="sm"
          onClick={() => downloadJSON(output, 'complete-meeting-results')}
          className="gap-2"
        >
          <Download className="w-4 h-4" />
          Download All Results (JSON)
        </Button>
      </div>

      {/* Summary */}
      <Card className="p-6 border-border bg-card/50 backdrop-blur-sm">
        <div className="flex items-center gap-2 mb-4">
          <FileText className="w-5 h-5 text-primary" />
          <h3 className="font-semibold text-foreground">Meeting Summary</h3>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => downloadJSON({ summary: output.summary }, 'meeting-summary')}
            className="ml-auto text-xs"
          >
            <Download className="w-4 h-4 mr-1" />
            JSON
          </Button>
        </div>
        <div className="prose prose-invert prose-sm max-w-none">
          <div className="whitespace-pre-wrap text-foreground/90 text-sm leading-relaxed">
            {output.summary}
          </div>
        </div>
      </Card>

      {/* Key Decisions - Enhanced UI */}
      <Card className="p-6 border-border bg-card/50 backdrop-blur-sm">
        <div className="flex items-center gap-2 mb-6">
          <CheckSquare className="w-5 h-5 text-success" />
          <h3 className="font-semibold text-foreground">Key Decisions</h3>
          <Badge variant="secondary" className="ml-2">
            {output.decisions?.length || 0}
          </Badge>
          
          {/* Sort Controls */}
          {output.decisions && output.decisions.length > 1 && (
            <div className="flex items-center gap-2 ml-4">
              <ArrowUpDown className="w-4 h-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Sort by:</span>
              <Select value={sortBy} onValueChange={(value: SortOption) => setSortBy(value)}>
                <SelectTrigger className="h-7 w-32 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="timestamp">
                    <div className="flex items-center gap-2">
                      <Clock className="w-3 h-3" />
                      <span>Timeline</span>
                    </div>
                  </SelectItem>
                  <SelectItem value="confidence">
                    <div className="flex items-center gap-2">
                      <Target className="w-3 h-3" />
                      <span>Confidence</span>
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}
          
          <div className="ml-auto flex items-center gap-2">
            <span className="text-xs text-muted-foreground">
              Enhanced with attribution & feedback
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => downloadJSON({ decisions: output.decisions }, 'key-decisions')}
              className="text-xs"
            >
              <Download className="w-4 h-4 mr-1" />
              JSON
            </Button>
          </div>
        </div>
        
        {sortedDecisions.length > 0 ? (
          <div className="space-y-4">
            {sortedDecisions.map((decision, idx) => (
              <EnhancedDecisionCard
                key={`${sortBy}-${idx}`}
                decision={decision}
                originalSegments={output.metadata?.original_segments || []}
                index={idx}
                displayNumber={idx + 1}
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            <CheckSquare className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>No key decisions identified in this meeting transcript.</p>
            <p className="text-xs mt-2">Try uploading a transcript with explicit decision-making discussions.</p>
          </div>
        )}
        
        {/* Sort Information */}
        {sortedDecisions.length > 1 && (
          <div className="mt-4 pt-4 border-t border-border/30">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              {sortBy === 'timestamp' ? (
                <>
                  <Clock className="w-3 h-3" />
                  <span>Sorted chronologically by when decisions were made during the meeting</span>
                </>
              ) : (
                <>
                  <Target className="w-3 h-3" />
                  <span>Sorted by model confidence level (highest confidence first)</span>
                </>
              )}
            </div>
          </div>
        )}
      </Card>

      {/* Actions */}
      <Card className="p-6 border-border bg-card/50 backdrop-blur-sm">
        <div className="flex items-center gap-2 mb-4">
          <CheckSquare className="w-5 h-5 text-accent" />
          <h3 className="font-semibold text-foreground">Action Items</h3>
          <Badge variant="secondary" className="ml-2">
            {output.action_items?.length || 0}
          </Badge>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => downloadJSON({ action_items: output.action_items }, 'action-items')}
            className="ml-auto text-xs"
          >
            <Download className="w-4 h-4 mr-1" />
            JSON
          </Button>
        </div>
        <div className="space-y-3">
          {output.action_items.map((action, idx) => (
            <ProvenanceView
              key={idx}
              item={action}
              itemType="action"
              originalSegments={output.metadata?.original_segments || []}
            />
          ))}
        </div>
      </Card>

      {/* Risks */}
      <Card className="p-6 border-border bg-card/50 backdrop-blur-sm">
        <div className="flex items-center gap-2 mb-4">
          <AlertTriangle className="w-5 h-5 text-warning" />
          <h3 className="font-semibold text-foreground">Identified Risks</h3>
          <Badge variant="secondary" className="ml-2">
            {output.risks?.length || 0}
          </Badge>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => downloadJSON({ risks: output.risks }, 'identified-risks')}
            className="ml-auto text-xs"
          >
            <Download className="w-4 h-4 mr-1" />
            JSON
          </Button>
        </div>
        <div className="space-y-3">
          {output.risks.map((risk, idx) => (
            <ProvenanceView
              key={idx}
              item={risk}
              itemType="risk"
              originalSegments={output.metadata?.original_segments || []}
            />
          ))}
        </div>
      </Card>

      {/* Speakers */}
      {output.metadata.speakers.length > 0 && (
        <Card className="p-6 border-border bg-card/50 backdrop-blur-sm">
          <div className="flex items-center gap-2 mb-4">
            <Users className="w-5 h-5 text-secondary" />
            <h3 className="font-semibold text-foreground">Meeting Participants</h3>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => downloadJSON({ participants: output.metadata.speakers, metadata: output.metadata }, 'meeting-metadata')}
              className="ml-auto text-xs"
            >
              <Download className="w-4 h-4 mr-1" />
              JSON
            </Button>
          </div>
          <div className="flex flex-wrap gap-2">
            {output.metadata.speakers.map((speaker, idx) => (
              <Badge key={idx} variant="outline">
                {speaker}
              </Badge>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
};
