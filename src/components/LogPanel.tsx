import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Terminal, X, ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useState } from 'react';

export interface LogEntry {
  id: string;
  timestamp: Date;
  level: 'info' | 'success' | 'error' | 'warning';
  message: string;
}

interface LogPanelProps {
  logs: LogEntry[];
  onClear?: () => void;
  className?: string;
}

export const LogPanel = ({ logs, onClear, className }: LogPanelProps) => {
  const [isExpanded, setIsExpanded] = useState(true);

  const getLevelColor = (level: LogEntry['level']) => {
    switch (level) {
      case 'success':
        return 'text-green-500';
      case 'error':
        return 'text-red-500';
      case 'warning':
        return 'text-yellow-500';
      default:
        return 'text-blue-500';
    }
  };

  const getLevelIcon = (level: LogEntry['level']) => {
    switch (level) {
      case 'success':
        return '✓';
      case 'error':
        return '✗';
      case 'warning':
        return '⚠';
      default:
        return 'ℹ';
    }
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  return (
    <Card className={cn('border-border bg-card/50 backdrop-blur-sm', className)}>
      <div className="p-4">
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Terminal className="w-4 h-4 text-muted-foreground" />
            <h3 className="font-semibold text-foreground text-sm">Activity Log</h3>
            {logs.length > 0 && (
              <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
                {logs.length}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {onClear && logs.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onClear}
                className="h-7 px-2 text-xs"
              >
                <X className="w-3 h-3 mr-1" />
                Clear
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsExpanded(!isExpanded)}
              className="h-7 px-2"
            >
              {isExpanded ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronUp className="w-4 h-4" />
              )}
            </Button>
          </div>
        </div>

        {/* Log Content */}
        {isExpanded && (
          <ScrollArea className="h-[300px] w-full">
            <div className="space-y-1 font-mono text-xs pr-4">
              {logs.length === 0 ? (
                <div className="text-muted-foreground p-4 text-center">
                  No activity yet. Upload a file to see logs.
                </div>
              ) : (
                logs.map((log) => (
                  <div
                    key={log.id}
                    className={cn(
                      'flex items-start gap-2 p-2 rounded hover:bg-muted/50 transition-colors',
                      log.level === 'error' && 'bg-destructive/5 border-l-2 border-destructive'
                    )}
                  >
                    <span className={cn('font-bold min-w-[1rem]', getLevelColor(log.level))}>
                      {getLevelIcon(log.level)}
                    </span>
                    <span className="text-muted-foreground min-w-[4rem]">
                      {formatTime(log.timestamp)}
                    </span>
                    <span className={cn('flex-1 break-words', getLevelColor(log.level))}>
                      {log.message}
                    </span>
                  </div>
                ))
              )}
            </div>
          </ScrollArea>
        )}
      </div>
    </Card>
  );
};
