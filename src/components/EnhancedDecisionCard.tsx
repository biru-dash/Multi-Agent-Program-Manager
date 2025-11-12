import React, { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Separator } from '@/components/ui/separator';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { 
  ChevronDown, 
  ChevronUp, 
  Clock, 
  User, 
  MessageSquare, 
  ThumbsUp, 
  ThumbsDown, 
  AlertTriangle,
  CheckCircle,
  Calendar,
  DollarSign,
  Settings,
  Shield,
  Users,
  Workflow,
  Tag,
  Eye,
  EyeOff,
  Send
} from 'lucide-react';
import { toast } from 'sonner';

interface DecisionFeedback {
  accuracy: 'accurate' | 'inaccurate' | null;
  structure: 'clear' | 'confusing' | null;
  usefulness: 'useful' | 'needs_recreation' | null;
  comments: string;
}

interface EnhancedDecisionProps {
  decision: {
    text?: string;
    decision?: string;
    title?: string;
    category?: string;
    participants?: string[];
    supporting_statements?: string[];
    quantitative_data?: {
      dates?: string[];
      numbers?: string[];
      changes?: string[];
    };
    confidence: number;
    decision_type?: 'explicit' | 'implicit';
    speaker?: string;
    timestamp?: string;
    provenance?: {
      source_segment_ids: number[];
      source_text: string[];
      similarity_scores: number[];
      extraction_method: string;
    };
    validation?: {
      is_valid: boolean;
      confidence: number;
      source_support: number;
      potential_hallucination?: boolean;
    };
  };
  originalSegments?: Array<{ text: string; speaker?: string; timestamp?: string }>;
  index: number;
  displayNumber: number; // Sorted position number
}

const getCategoryIcon = (category: string) => {
  switch (category?.toLowerCase()) {
    case 'timeline': return <Calendar className="w-4 h-4" />;
    case 'features': return <Settings className="w-4 h-4" />;
    case 'budget': return <DollarSign className="w-4 h-4" />;
    case 'security': return <Shield className="w-4 h-4" />;
    case 'communication': return <MessageSquare className="w-4 h-4" />;
    case 'resources': return <Users className="w-4 h-4" />;
    case 'process': return <Workflow className="w-4 h-4" />;
    default: return null; // Don't show icon for 'other' category
  }
};

const getCategoryColor = (category: string) => {
  switch (category?.toLowerCase()) {
    case 'timeline': return 'bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800';
    case 'features': return 'bg-purple-100 text-purple-800 border-purple-200 dark:bg-purple-900/30 dark:text-purple-400 dark:border-purple-800';
    case 'budget': return 'bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800';
    case 'security': return 'bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800';
    case 'communication': return 'bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-900/30 dark:text-orange-400 dark:border-orange-800';
    case 'resources': return 'bg-cyan-100 text-cyan-800 border-cyan-200 dark:bg-cyan-900/30 dark:text-cyan-400 dark:border-cyan-800';
    case 'process': return 'bg-indigo-100 text-indigo-800 border-indigo-200 dark:bg-indigo-900/30 dark:text-indigo-400 dark:border-indigo-800';
    default: return null; // Don't show badge for 'other' category
  }
};

const getConfidenceBadge = (confidence: number, decisionType?: string) => {
  if (confidence >= 0.8) {
    return { 
      label: decisionType === 'implicit' ? 'High (Inferred)' : 'High', 
      variant: 'default' as const, 
      className: 'bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-400' 
    };
  }
  if (confidence >= 0.6) {
    return { 
      label: decisionType === 'implicit' ? 'Medium (Inferred)' : 'Medium', 
      variant: 'secondary' as const, 
      className: 'bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-400' 
    };
  }
  return { 
    label: decisionType === 'implicit' ? 'Low (Inferred)' : 'Low', 
    variant: 'outline' as const, 
    className: 'bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-400' 
  };
};

export const EnhancedDecisionCard: React.FC<EnhancedDecisionProps> = ({ 
  decision, 
  originalSegments = [], 
  index,
  displayNumber
}) => {
  const [showDetails, setShowDetails] = useState(false);
  const [showProvenance, setShowProvenance] = useState(false);
  const [feedback, setFeedback] = useState<DecisionFeedback>({
    accuracy: null,
    structure: null,
    usefulness: null,
    comments: ''
  });
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);

  const decisionText = decision.decision || decision.text || '';
  const title = decision.title || 'Decision';
  const category = decision.category || 'other';
  const participants = decision.participants || [decision.speaker].filter(Boolean);
  const confidence = decision.confidence || 0.5;
  const confidenceBadge = getConfidenceBadge(confidence, decision.decision_type);

  // Extract attribution information
  const getAttributionInfo = () => {
    if (decision.provenance?.source_segment_ids && originalSegments.length > 0) {
      const sourceSegments = decision.provenance.source_segment_ids
        .map(id => originalSegments[id])
        .filter(Boolean);
      
      if (sourceSegments.length > 0) {
        const primarySegment = sourceSegments[0];
        return {
          speaker: primarySegment.speaker || 'Unknown',
          timestamp: primarySegment.timestamp || 'Unknown time',
          context: sourceSegments.map(s => s.text).join(' ')
        };
      }
    }
    
    return {
      speaker: participants[0] || decision.speaker || 'Unknown',
      timestamp: decision.timestamp || 'Unknown time',
      context: decisionText
    };
  };

  const attribution = getAttributionInfo();

  const handleFeedbackSubmit = () => {
    // Here you would typically send feedback to an API
    console.log('Decision Feedback:', {
      decisionIndex: index,
      decisionText,
      feedback
    });
    
    setFeedbackSubmitted(true);
    setShowFeedback(false);
    toast.success('Thank you for your feedback! This helps improve the AI analysis.');
  };

  const resetFeedback = () => {
    setFeedback({
      accuracy: null,
      structure: null,
      usefulness: null,
      comments: ''
    });
    setFeedbackSubmitted(false);
  };

  return (
    <Card className="group hover:shadow-md transition-all duration-200 border border-border/50 bg-card/30 backdrop-blur-sm">
      {/* Header with Number, Category and Confidence */}
      <div className="p-4 pb-3">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-3 flex-1">
            {/* Decision Number */}
            <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary/10 border border-primary/20 text-primary font-semibold text-sm">
              {displayNumber}
            </div>
            
            <div className="flex items-center gap-2">
              {getCategoryColor(category) && getCategoryIcon(category) && (
                <Badge className={`${getCategoryColor(category)} border px-2 py-1 text-xs font-medium`}>
                  {getCategoryIcon(category)}
                  <span className="ml-1 capitalize">{category}</span>
                </Badge>
              )}
              <Badge className={`${confidenceBadge.className} border px-2 py-1 text-xs`}>
                {confidenceBadge.label}
              </Badge>
              {decision.decision_type === 'implicit' && (
                <Badge variant="outline" className="px-2 py-1 text-xs border-dashed">
                  Inferred
                </Badge>
              )}
            </div>
          </div>
          <div className="flex items-center gap-1">
            {feedbackSubmitted && (
              <CheckCircle className="w-4 h-4 text-green-500" />
            )}
          </div>
        </div>

        {/* Content */}
        <p className="text-sm text-foreground/90 leading-relaxed mb-3">
          {decisionText}
        </p>

        {/* Attribution Bar */}
        <div className="flex items-center gap-4 p-3 bg-muted/30 rounded-lg border border-border/30">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <User className="w-4 h-4" />
            <span className="font-medium">{attribution.speaker}</span>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Clock className="w-4 h-4" />
            <span>{attribution.timestamp}</span>
          </div>
          {participants.length > 1 && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Users className="w-4 h-4" />
              <span>{participants.length} participants</span>
            </div>
          )}
        </div>

      </div>

      {/* Action Buttons */}
      <div className="px-4 pb-4">
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowDetails(!showDetails)}
            className="text-xs h-8"
          >
            {showDetails ? <ChevronUp className="w-3 h-3 mr-1" /> : <ChevronDown className="w-3 h-3 mr-1" />}
            Details
          </Button>
          
          {decision.provenance && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowProvenance(!showProvenance)}
              className="text-xs h-8"
            >
              {showProvenance ? <EyeOff className="w-3 h-3 mr-1" /> : <Eye className="w-3 h-3 mr-1" />}
              Sources
            </Button>
          )}
          
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowFeedback(!showFeedback)}
            className="text-xs h-8 ml-auto"
            disabled={feedbackSubmitted}
          >
            <MessageSquare className="w-3 h-3 mr-1" />
            {feedbackSubmitted ? 'Feedback Sent' : 'Feedback'}
          </Button>
        </div>
      </div>

      {/* Collapsible Details */}
      <Collapsible open={showDetails} onOpenChange={setShowDetails}>
        <CollapsibleContent>
          <div className="px-4 pb-4 border-t border-border/30">
            <div className="pt-3 space-y-3">
              {/* Supporting Statements */}
              {decision.supporting_statements && decision.supporting_statements.length > 0 && (
                <div>
                  <h5 className="text-sm font-medium text-foreground mb-2">Supporting Context</h5>
                  <div className="space-y-2">
                    {decision.supporting_statements.map((statement, idx) => (
                      <div key={idx} className="text-xs p-2 bg-muted/30 rounded border-l-2 border-primary/30">
                        "{statement}"
                      </div>
                    ))}
                  </div>
                </div>
              )}


              {/* Validation Info */}
              {decision.validation && (
                <div>
                  <h5 className="text-sm font-medium text-foreground mb-2">Validation</h5>
                  <div className="flex items-center gap-3 text-xs">
                    <div className="flex items-center gap-1">
                      {decision.validation.is_valid ? (
                        <CheckCircle className="w-3 h-3 text-green-500" />
                      ) : (
                        <AlertTriangle className="w-3 h-3 text-yellow-500" />
                      )}
                      <span>{decision.validation.is_valid ? 'Validated' : 'Needs Review'}</span>
                    </div>
                    <div>Source Support: {(decision.validation.source_support * 100).toFixed(0)}%</div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </CollapsibleContent>
      </Collapsible>

      {/* Provenance Sources */}
      <Collapsible open={showProvenance} onOpenChange={setShowProvenance}>
        <CollapsibleContent>
          <div className="px-4 pb-4 border-t border-border/30">
            <div className="pt-3">
              <h5 className="text-sm font-medium text-foreground mb-2">Source Segments</h5>
              {decision.provenance?.source_text?.map((text, idx) => (
                <div key={idx} className="mb-2 p-2 bg-muted/20 rounded text-xs border-l-2 border-blue-400/30">
                  <div className="font-medium text-blue-600 dark:text-blue-400 mb-1">
                    Similarity: {decision.provenance?.similarity_scores?.[idx] 
                      ? (decision.provenance.similarity_scores[idx] * 100).toFixed(0) + '%' 
                      : 'N/A'}
                  </div>
                  <div>"{text}"</div>
                </div>
              ))}
            </div>
          </div>
        </CollapsibleContent>
      </Collapsible>

      {/* Feedback Form */}
      <Collapsible open={showFeedback} onOpenChange={setShowFeedback}>
        <CollapsibleContent>
          <div className="px-4 pb-4 border-t border-border/30">
            <div className="pt-3 space-y-4">
              <h5 className="text-sm font-medium text-foreground">Provide Feedback</h5>
              
              {/* Accuracy Rating */}
              <div>
                <label className="text-xs font-medium text-muted-foreground mb-2 block">
                  Is this decision accurate?
                </label>
                <div className="flex gap-2">
                  <Button
                    variant={feedback.accuracy === 'accurate' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setFeedback(f => ({ ...f, accuracy: 'accurate' }))}
                    className="h-8 text-xs"
                  >
                    <ThumbsUp className="w-3 h-3 mr-1" />
                    Accurate
                  </Button>
                  <Button
                    variant={feedback.accuracy === 'inaccurate' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setFeedback(f => ({ ...f, accuracy: 'inaccurate' }))}
                    className="h-8 text-xs"
                  >
                    <ThumbsDown className="w-3 h-3 mr-1" />
                    Inaccurate
                  </Button>
                </div>
              </div>

              {/* Structure Rating */}
              <div>
                <label className="text-xs font-medium text-muted-foreground mb-2 block">
                  Is the structure clear and easy to understand?
                </label>
                <div className="flex gap-2">
                  <Button
                    variant={feedback.structure === 'clear' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setFeedback(f => ({ ...f, structure: 'clear' }))}
                    className="h-8 text-xs"
                  >
                    Clear
                  </Button>
                  <Button
                    variant={feedback.structure === 'confusing' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setFeedback(f => ({ ...f, structure: 'confusing' }))}
                    className="h-8 text-xs"
                  >
                    Confusing
                  </Button>
                </div>
              </div>

              {/* Usefulness Rating */}
              <div>
                <label className="text-xs font-medium text-muted-foreground mb-2 block">
                  Is this decision useful as extracted?
                </label>
                <div className="flex gap-2">
                  <Button
                    variant={feedback.usefulness === 'useful' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setFeedback(f => ({ ...f, usefulness: 'useful' }))}
                    className="h-8 text-xs"
                  >
                    Good to use
                  </Button>
                  <Button
                    variant={feedback.usefulness === 'needs_recreation' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setFeedback(f => ({ ...f, usefulness: 'needs_recreation' }))}
                    className="h-8 text-xs"
                  >
                    Needs recreation
                  </Button>
                </div>
              </div>

              {/* Comments */}
              <div>
                <label className="text-xs font-medium text-muted-foreground mb-2 block">
                  Additional comments (optional)
                </label>
                <Textarea
                  value={feedback.comments}
                  onChange={(e) => setFeedback(f => ({ ...f, comments: e.target.value }))}
                  placeholder="Any specific feedback about this decision..."
                  className="text-xs"
                  rows={2}
                />
              </div>

              {/* Submit Buttons */}
              <div className="flex gap-2 pt-2">
                <Button
                  onClick={handleFeedbackSubmit}
                  size="sm"
                  className="h-8 text-xs"
                  disabled={!feedback.accuracy && !feedback.structure && !feedback.usefulness}
                >
                  <Send className="w-3 h-3 mr-1" />
                  Submit Feedback
                </Button>
                <Button
                  variant="outline"
                  onClick={resetFeedback}
                  size="sm"
                  className="h-8 text-xs"
                >
                  Reset
                </Button>
              </div>
            </div>
          </div>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
};