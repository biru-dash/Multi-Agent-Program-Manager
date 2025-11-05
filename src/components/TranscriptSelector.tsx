import { useState, useEffect } from 'react';
import { FolderOpen, FileText, Loader2, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { miaService, type TranscriptFile } from '@/services/miaService';
import { cn } from '@/lib/utils';

interface TranscriptSelectorProps {
  onTranscriptSelected: (filename: string, uploadId: string) => void;
  selectedFilename?: string | null;
}

export const TranscriptSelector = ({
  onTranscriptSelected,
  selectedFilename,
}: TranscriptSelectorProps) => {
  const [transcripts, setTranscripts] = useState<TranscriptFile[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const loadTranscripts = async () => {
    setIsLoading(true);
    try {
      const files = await miaService.listTranscripts();
      setTranscripts(files);
      if (files.length === 0) {
        toast.info('No transcript files found in meeting_transcripts folder');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load transcripts';
      toast.error(errorMessage);
      console.error('Error loading transcripts:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      const files = await miaService.listTranscripts();
      setTranscripts(files);
      toast.success(`Found ${files.length} transcript file(s)`);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to refresh transcripts';
      toast.error(errorMessage);
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleSelect = async (filename: string) => {
    try {
      const response = await miaService.selectTranscript(filename);
      onTranscriptSelected(filename, response.upload_id);
      toast.success(`Selected: ${filename}`);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to select transcript';
      toast.error(errorMessage);
    }
  };

  useEffect(() => {
    loadTranscripts();
  }, []);

  if (isLoading) {
    return (
      <Card className="p-6">
        <div className="flex items-center justify-center gap-3">
          <Loader2 className="w-5 h-5 animate-spin text-primary" />
          <span className="text-muted-foreground">Loading transcript files...</span>
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <FolderOpen className="w-5 h-5 text-primary" />
          <h3 className="font-semibold">Select from Meeting Transcripts</h3>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
          disabled={isRefreshing}
          className="gap-2"
        >
          <RefreshCw className={cn("w-4 h-4", isRefreshing && "animate-spin")} />
          Refresh
        </Button>
      </div>

      {transcripts.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p className="font-medium mb-1">No transcript files found</p>
          <p className="text-sm">
            Place transcript files (.txt, .json, .srt) in the <code className="px-1 py-0.5 bg-muted rounded">meeting_transcripts</code> folder
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {transcripts.map((transcript) => (
            <Button
              key={transcript.filename}
              variant={selectedFilename === transcript.filename ? "default" : "outline"}
              className={cn(
                "w-full justify-start gap-3 h-auto py-3",
                selectedFilename === transcript.filename && "bg-primary text-primary-foreground"
              )}
              onClick={() => handleSelect(transcript.filename)}
            >
              <FileText className="w-5 h-5 flex-shrink-0" />
              <div className="flex-1 text-left min-w-0">
                <div className="font-medium truncate">{transcript.filename}</div>
                <div className="text-xs opacity-70 mt-0.5">
                  {transcript.size_mb.toFixed(2)} MB
                </div>
              </div>
              {selectedFilename === transcript.filename && (
                <div className="w-2 h-2 rounded-full bg-current opacity-70" />
              )}
            </Button>
          ))}
        </div>
      )}
    </Card>
  );
};

