import { REAOutput as REAOutputType } from '@/types/agent';
import { Card } from '@/components/ui/card';
import { FileText, ArrowUpCircle, MinusCircle, ArrowDownCircle } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface REAOutputProps {
  output: REAOutputType | null;
}

export const REAOutput = ({ output }: REAOutputProps) => {
  if (!output) {
    return (
      <Card className="p-8 text-center border-border bg-card/50">
        <FileText className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
        <p className="text-muted-foreground">
          Process a transcript to see extracted requirements
        </p>
      </Card>
    );
  }

  const getPriorityIcon = (priority: string) => {
    switch (priority) {
      case 'high':
        return <ArrowUpCircle className="w-4 h-4 text-destructive" />;
      case 'medium':
        return <MinusCircle className="w-4 h-4 text-warning" />;
      case 'low':
        return <ArrowDownCircle className="w-4 h-4 text-success" />;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'bg-destructive/10 text-destructive border-destructive/20';
      case 'medium':
        return 'bg-warning/10 text-warning border-warning/20';
      case 'low':
        return 'bg-success/10 text-success border-success/20';
    }
  };

  return (
    <div className="space-y-4">
      {output.userStories.map((story) => (
        <Card
          key={story.id}
          className="p-6 border-border bg-card/50 backdrop-blur-sm hover:border-primary/50 transition-colors"
        >
          {/* Header */}
          <div className="flex items-start justify-between mb-4">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <Badge variant="outline" className="font-mono text-xs">
                  {story.id}
                </Badge>
                <Badge
                  className={cn('flex items-center gap-1', getPriorityColor(story.priority))}
                >
                  {getPriorityIcon(story.priority)}
                  {story.priority}
                </Badge>
              </div>
              <h3 className="font-semibold text-foreground text-lg">{story.title}</h3>
            </div>
          </div>

          {/* Description */}
          <div className="mb-4 p-4 rounded-lg bg-muted/30 border border-border/50">
            <p className="text-sm text-foreground/90 italic">{story.description}</p>
          </div>

          {/* Acceptance Criteria */}
          <div>
            <h4 className="text-sm font-semibold text-foreground mb-3">
              Acceptance Criteria
            </h4>
            <ul className="space-y-2">
              {story.acceptanceCriteria.map((criterion, idx) => (
                <li key={idx} className="flex items-start gap-3 text-sm">
                  <span className="text-primary mt-1">✓</span>
                  <span className="text-foreground/80">{criterion}</span>
                </li>
              ))}
            </ul>
          </div>
        </Card>
      ))}

      {/* Sprint Priorities Summary */}
      <Card className="p-6 border-border bg-card/50 backdrop-blur-sm">
        <h3 className="font-semibold text-foreground mb-4 flex items-center gap-2">
          <FileText className="w-5 h-5 text-secondary" />
          Sprint Priorities
        </h3>
        <ul className="space-y-2">
          {output.priorities.map((priority, idx) => (
            <li key={idx} className="flex items-start gap-3 text-sm">
              <span className="text-secondary font-bold">{idx + 1}.</span>
              <span className="text-foreground/90">{priority}</span>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
};
