import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  Calendar,
  Clock,
  DollarSign,
  MessageSquare,
  Settings,
  Shield,
  User,
  Users as UsersIcon,
  Workflow,
} from 'lucide-react';

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
  };
  originalSegments?: Array<{ text: string; speaker?: string; timestamp?: string }>;
  index: number;
  displayNumber: number;
}

const getCategoryIcon = (category: string) => {
  switch (category?.toLowerCase()) {
    case 'timeline':
      return <Calendar className="w-4 h-4" />;
    case 'features':
      return <Settings className="w-4 h-4" />;
    case 'budget':
      return <DollarSign className="w-4 h-4" />;
    case 'security':
      return <Shield className="w-4 h-4" />;
    case 'communication':
      return <MessageSquare className="w-4 h-4" />;
    case 'resources':
      return <UsersIcon className="w-4 h-4" />;
    case 'process':
      return <Workflow className="w-4 h-4" />;
    default:
      return null;
  }
};

const getCategoryColor = (category: string) => {
  switch (category?.toLowerCase()) {
    case 'timeline':
      return 'bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800';
    case 'features':
      return 'bg-purple-100 text-purple-800 border-purple-200 dark:bg-purple-900/30 dark:text-purple-400 dark:border-purple-800';
    case 'budget':
      return 'bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800';
    case 'security':
      return 'bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800';
    case 'communication':
      return 'bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-900/30 dark:text-orange-400 dark:border-orange-800';
    case 'resources':
      return 'bg-cyan-100 text-cyan-800 border-cyan-200 dark:bg-cyan-900/30 dark:text-cyan-400 dark:border-cyan-800';
    case 'process':
      return 'bg-indigo-100 text-indigo-800 border-indigo-200 dark:bg-indigo-900/30 dark:text-indigo-400 dark:border-indigo-800';
    default:
      return null;
  }
};

const getConfidenceBadge = (confidence: number, decisionType?: string) => {
  if (confidence >= 0.8) {
    return {
      label: decisionType === 'implicit' ? 'High (Inferred)' : 'High',
      className: 'bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-400',
    };
  }
  if (confidence >= 0.6) {
    return {
      label: decisionType === 'implicit' ? 'Medium (Inferred)' : 'Medium',
      className: 'bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-400',
    };
  }
  return {
    label: decisionType === 'implicit' ? 'Low (Inferred)' : 'Low',
    className: 'bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-400',
  };
};

export const EnhancedDecisionCard: React.FC<EnhancedDecisionProps> = ({
  decision,
  originalSegments = [],
  displayNumber,
}) => {
  const decisionText = decision.decision || decision.text || '';
  const title = decision.title || 'Decision';
  const category = decision.category || 'other';
  const participants = decision.participants || [decision.speaker].filter(Boolean);
  const confidence = decision.confidence || 0.5;
  const confidenceBadge = getConfidenceBadge(confidence, decision.decision_type);

  const getAttributionInfo = () => {
    if (decision.provenance?.source_segment_ids && originalSegments.length > 0) {
      const sourceSegments = decision.provenance.source_segment_ids
        .map((id) => originalSegments[id])
        .filter(Boolean);

      if (sourceSegments.length > 0) {
        const primarySegment = sourceSegments[0];
        return {
          speaker: primarySegment.speaker || 'Unknown',
          timestamp: primarySegment.timestamp || 'Unknown time',
        };
      }
    }

    return {
      speaker: participants[0] || decision.speaker || 'Unknown',
      timestamp: decision.timestamp || 'Unknown time',
    };
  };

  const attribution = getAttributionInfo();
  const quantitative = decision.quantitative_data;
  const hasQuantitative = Boolean(
    quantitative && (
      (quantitative.dates && quantitative.dates.length > 0) ||
      (quantitative.numbers && quantitative.numbers.length > 0) ||
      (quantitative.changes && quantitative.changes.length > 0)
    )
  );

  return (
    <div className="rounded-lg border border-border/40 bg-card/30 p-4">
      <div className="flex items-start gap-3 mb-3">
        <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary/10 border border-primary/20 text-primary font-semibold text-sm">
          {displayNumber}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline" className="px-2 py-1 text-xs font-medium">
            {title}
          </Badge>
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

      <p className="text-sm text-foreground/90 leading-relaxed mb-3">{decisionText}</p>

      <div className="flex flex-wrap items-center gap-3 p-3 bg-muted/20 rounded-lg border border-border/30 text-xs text-muted-foreground mb-3">
        <div className="flex items-center gap-2">
          <User className="w-4 h-4" />
          <span className="font-medium">{attribution.speaker}</span>
        </div>
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4" />
          <span>{attribution.timestamp}</span>
        </div>
        {participants.length > 1 && (
          <div className="flex items-center gap-2">
            <UsersIcon className="w-4 h-4" />
            <span>{participants.length} participants</span>
          </div>
        )}
      </div>

      {hasQuantitative && (
        <div className="flex flex-wrap gap-3 text-xs text-muted-foreground mb-3">
          {quantitative?.dates && quantitative.dates.length > 0 && (
            <div className="flex items-center gap-1">
              <Calendar className="w-3 h-3" />
              <span>{quantitative.dates.join(', ')}</span>
            </div>
          )}
          {quantitative?.numbers && quantitative.numbers.length > 0 && (
            <div className="flex items-center gap-1">
              <DollarSign className="w-3 h-3" />
              <span>{quantitative.numbers.join(', ')}</span>
            </div>
          )}
          {quantitative?.changes && quantitative.changes.length > 0 && (
            <div className="flex items-center gap-1">
              <Workflow className="w-3 h-3" />
              <span>{quantitative.changes.join(', ')}</span>
            </div>
          )}
        </div>
      )}

      {decision.supporting_statements && decision.supporting_statements.length > 0 && (
        <div>
          <Separator className="my-3" />
          <h5 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            Supporting statements
          </h5>
          <ul className="space-y-2 text-xs text-muted-foreground">
            {decision.supporting_statements.slice(0, 3).map((statement, idx) => (
              <li key={idx} className="pl-3 border-l border-border/40">“{statement}”</li>
            ))}
          </ul>
        </div>
      )}

      {decision.provenance?.source_text && decision.provenance.source_text.length > 0 && (
        <div>
          <Separator className="my-3" />
          <h5 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            Source excerpts
          </h5>
          <ul className="space-y-2 text-xs text-muted-foreground">
            {decision.provenance.source_text.slice(0, 2).map((text, idx) => (
              <li key={idx} className="pl-3 border-l border-blue-400/30">“{text}”</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};