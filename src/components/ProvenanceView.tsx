import React, { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { 
  Eye, EyeOff, CheckCircle, XCircle, AlertTriangle, 
  ChevronDown, ChevronUp, FileText 
} from 'lucide-react';

interface ProvenanceInfo {
  source_segment_ids: number[];
  source_text: string[];
  similarity_scores: number[];
  extraction_method: string;
}

interface ValidationInfo {
  is_valid: boolean;
  confidence: number;
  issues: Array<{
    type: string;
    severity: string;
    message: string;
  }>;
  source_support: number;
  word_overlap: number;
  potential_hallucination?: boolean;
  warning?: string;
}

interface ProvenanceViewProps {
  item: {
    text?: string;
    decision?: string;
    action?: string;
    risk?: string;
    confidence: number;
    provenance?: ProvenanceInfo;
    validation?: ValidationInfo;
  };
  originalSegments?: Array<{ text: string; speaker?: string; timestamp?: string }>;
  itemType: 'decision' | 'action' | 'risk';
}

export const ProvenanceView: React.FC<ProvenanceViewProps> = ({ 
  item, 
  originalSegments = [],
  itemType 
}) => {
  const [showProvenance, setShowProvenance] = useState(false);
  const [highlightedSegments, setHighlightedSegments] = useState<number[]>([]);

  const itemText = item.text || item.decision || item.action || item.risk || '';
  const provenance = item.provenance;
  const validation = item.validation;

  const getValidationBadge = () => {
    if (!validation) return null;

    if (validation.potential_hallucination) {
      return (
        <Badge variant="destructive" className="text-xs">
          <AlertTriangle className="w-3 h-3 mr-1" />
          Potential Issue
        </Badge>
      );
    }

    if (validation.is_valid) {
      return (
        <Badge variant="default" className="text-xs">
          <CheckCircle className="w-3 h-3 mr-1" />
          Validated
        </Badge>
      );
    }

    return (
      <Badge variant="outline" className="text-xs">
        <XCircle className="w-3 h-3 mr-1" />
        Needs Review
      </Badge>
    );
  };

  const getConfidenceBadge = (confidence: number) => {
    if (confidence >= 0.8) return { label: 'High', variant: 'default' as const };
    if (confidence >= 0.6) return { label: 'Medium', variant: 'secondary' as const };
    return { label: 'Low', variant: 'outline' as const };
  };

  const confidenceBadge = getConfidenceBadge(item.confidence);

  const handleShowSource = () => {
    if (provenance?.source_segment_ids) {
      setHighlightedSegments(provenance.source_segment_ids);
    }
    setShowProvenance(!showProvenance);
  };

  return (
    <Card className="p-4 space-y-3">
      {/* Item Content */}
      <div className="space-y-2">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <p className="text-sm text-foreground">{itemText}</p>
          </div>
          <div className="flex items-center gap-2 ml-4">
            <Badge variant={confidenceBadge.variant} className="text-xs">
              {confidenceBadge.label}
            </Badge>
            {getValidationBadge()}
          </div>
        </div>

        {/* Validation Issues */}
        {validation?.issues && validation.issues.length > 0 && (
          <div className="space-y-1">
            {validation.issues.map((issue, idx) => (
              <div key={idx} className={`text-xs p-2 rounded ${
                issue.severity === 'high' ? 'bg-red-50 text-red-700' :
                issue.severity === 'medium' ? 'bg-yellow-50 text-yellow-700' :
                'bg-blue-50 text-blue-700'
              }`}>
                <span className="font-medium">{issue.type}:</span> {issue.message}
              </div>
            ))}
          </div>
        )}

        {/* Provenance Controls */}
        {provenance && (
          <div className="flex items-center gap-2 pt-2 border-t">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleShowSource}
              className="text-xs"
            >
              {showProvenance ? <EyeOff className="w-4 h-4 mr-1" /> : <Eye className="w-4 h-4 mr-1" />}
              {showProvenance ? 'Hide' : 'Show'} Source
            </Button>
            
            {provenance.similarity_scores && provenance.similarity_scores.length > 0 && (
              <Badge variant="outline" className="text-xs">
                {Math.round(Math.max(...provenance.similarity_scores) * 100)}% match
              </Badge>
            )}
            
            <Badge variant="outline" className="text-xs">
              {provenance.extraction_method}
            </Badge>
          </div>
        )}
      </div>

      {/* Provenance Details */}
      <Collapsible open={showProvenance} onOpenChange={setShowProvenance}>
        <CollapsibleContent className="space-y-3">
          {provenance && (
            <div className="bg-muted/50 rounded-lg p-3 space-y-3">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4" />
                <span className="text-sm font-medium">Source Segments</span>
              </div>
              
              {/* Source Segments */}
              <div className="space-y-2">
                {provenance.source_segment_ids.map((segmentId, idx) => {
                  const segment = originalSegments[segmentId];
                  const similarity = provenance.similarity_scores?.[idx] || 0;
                  
                  if (!segment) return null;
                  
                  return (
                    <div key={segmentId} className="bg-background rounded p-2 border">
                      <div className="flex items-start justify-between mb-1">
                        <span className="text-xs text-muted-foreground">
                          Segment #{segmentId + 1}
                          {segment.speaker && ` • ${segment.speaker}`}
                          {segment.timestamp && ` • ${segment.timestamp}`}
                        </span>
                        <Badge variant="outline" className="text-xs">
                          {Math.round(similarity * 100)}% similar
                        </Badge>
                      </div>
                      <p className="text-sm text-foreground">{segment.text}</p>
                    </div>
                  );
                })}
              </div>

              {/* Validation Details */}
              {validation && (
                <div className="pt-2 border-t space-y-2">
                  <span className="text-sm font-medium">Validation Details</span>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className="text-muted-foreground">Source Support:</span>
                      <span className="ml-1 font-medium">
                        {Math.round(validation.source_support * 100)}%
                      </span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Word Overlap:</span>
                      <span className="ml-1 font-medium">
                        {Math.round(validation.word_overlap * 100)}%
                      </span>
                    </div>
                  </div>
                  
                  {validation.warning && (
                    <div className="text-xs p-2 bg-yellow-50 text-yellow-700 rounded">
                      <AlertTriangle className="w-3 h-3 inline mr-1" />
                      {validation.warning}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
};

export default ProvenanceView;