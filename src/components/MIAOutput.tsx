import { Card } from '@/components/ui/card';
import { FileText, CheckSquare, AlertTriangle, Users } from 'lucide-react';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { type MIAResults } from '@/services/miaService';

interface MIAOutputProps {
  output: MIAResults | null;
}

const getConfidenceBadge = (confidence: number) => {
  if (confidence >= 0.8) return { label: 'High', variant: 'default' as const, color: 'text-green-500' };
  if (confidence >= 0.6) return { label: 'Medium', variant: 'secondary' as const, color: 'text-yellow-500' };
  return { label: 'Low', variant: 'outline' as const, color: 'text-red-500' };
};

export const MIAOutput = ({ output }: MIAOutputProps) => {
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
      {/* Summary */}
      <Card className="p-6 border-border bg-card/50 backdrop-blur-sm">
        <div className="flex items-center gap-2 mb-4">
          <FileText className="w-5 h-5 text-primary" />
          <h3 className="font-semibold text-foreground">Meeting Summary</h3>
        </div>
        <div className="prose prose-invert prose-sm max-w-none">
          <div className="whitespace-pre-wrap text-foreground/90 text-sm leading-relaxed">
            {output.summary}
          </div>
        </div>
      </Card>

      {/* Decisions */}
      <Card className="p-6 border-border bg-card/50 backdrop-blur-sm">
        <div className="flex items-center gap-2 mb-4">
          <CheckSquare className="w-5 h-5 text-success" />
          <h3 className="font-semibold text-foreground">Key Decisions</h3>
          <Badge variant="secondary" className="ml-auto">
            {output.decisions?.length || 0}
          </Badge>
        </div>
        <ul className="space-y-3">
          {output.decisions.map((decision, idx) => {
            const confidence = getConfidenceBadge(decision.confidence);
            return (
              <li key={idx} className="flex items-start gap-3 text-sm">
                <span className="text-success mt-1">•</span>
                <div className="flex-1">
                  <span className="text-foreground/90">{decision.text}</span>
                  {decision.speaker && (
                    <span className="text-muted-foreground text-xs ml-2">— {decision.speaker}</span>
                  )}
                  <Badge variant={confidence.variant} className="ml-2 text-xs">
                    {confidence.label} Confidence
                  </Badge>
                </div>
              </li>
            );
          })}
        </ul>
      </Card>

      {/* Actions */}
      <Card className="p-6 border-border bg-card/50 backdrop-blur-sm">
        <div className="flex items-center gap-2 mb-4">
          <CheckSquare className="w-5 h-5 text-accent" />
          <h3 className="font-semibold text-foreground">Action Items</h3>
          <Badge variant="secondary" className="ml-auto">
            {output.action_items?.length || 0}
          </Badge>
        </div>
        <ul className="space-y-3">
          {output.action_items.map((action, idx) => {
            const confidence = getConfidenceBadge(action.confidence);
            return (
              <li key={idx} className="flex items-start gap-3 text-sm">
                <span className="text-accent mt-1">•</span>
                <div className="flex-1">
                  <div className="text-foreground/90 font-medium">{action.action}</div>
                  <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                    {action.owner && <span>Owner: {action.owner}</span>}
                    {action.due_date && <span>• Due: {action.due_date}</span>}
                    <Badge variant={confidence.variant} className="text-xs">
                      {action.priority.toUpperCase()} • {confidence.label}
                    </Badge>
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      </Card>

      {/* Risks */}
      <Card className="p-6 border-border bg-card/50 backdrop-blur-sm">
        <div className="flex items-center gap-2 mb-4">
          <AlertTriangle className="w-5 h-5 text-warning" />
          <h3 className="font-semibold text-foreground">Identified Risks</h3>
          <Badge variant="secondary" className="ml-auto">
            {output.risks?.length || 0}
          </Badge>
        </div>
        <ul className="space-y-3">
          {output.risks.map((risk, idx) => {
            const confidence = getConfidenceBadge(risk.confidence);
            return (
              <li key={idx} className="flex items-start gap-3 text-sm">
                <span className="text-warning mt-1">⚠</span>
                <div className="flex-1">
                  <span className="text-foreground/90">{risk.risk}</span>
                  {risk.mentioned_by && (
                    <span className="text-muted-foreground text-xs ml-2">— mentioned by {risk.mentioned_by}</span>
                  )}
                  <Badge variant={confidence.variant} className="ml-2 text-xs">
                    {confidence.label} Confidence
                  </Badge>
                </div>
              </li>
            );
          })}
        </ul>
      </Card>

      {/* Speakers */}
      {output.metadata.speakers.length > 0 && (
        <Card className="p-6 border-border bg-card/50 backdrop-blur-sm">
          <div className="flex items-center gap-2 mb-4">
            <Users className="w-5 h-5 text-secondary" />
            <h3 className="font-semibold text-foreground">Meeting Participants</h3>
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
