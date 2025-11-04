import { Download, FileJson, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { type MIAResults, miaService } from '@/services/miaService';

interface ExportButtonsProps {
  miaOutput: MIAResults | null;
  reaOutput?: null; // Keep for compatibility but not used
  format: 'json' | 'markdown';
  jobId?: string | null;
}

export const ExportButtons = ({ miaOutput, format, jobId }: ExportButtonsProps) => {
  const exportMIAFromServer = async (formatType: 'json' | 'md') => {
    if (!jobId) {
      toast.error('No job ID available for export');
      return;
    }

    try {
      const blob = await miaService.exportResults(jobId, formatType);
      const filename = `mia_report_${jobId}.${formatType}`;
      miaService.downloadFile(blob, filename);
      toast.success(`Exported MIA results as ${formatType.toUpperCase()}`);
    } catch (error) {
      toast.error(`Export failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const exportData = async () => {
    // If we have a jobId and MIA output, try server export first
    if (jobId && miaOutput) {
      const formatMap: Record<string, 'json' | 'md'> = {
        'json': 'json',
        'markdown': 'md',
      };
      
      if (format in formatMap) {
        await exportMIAFromServer(formatMap[format]);
        return;
      }
    }

    // Fallback to client-side export
    if (!miaOutput) {
      toast.error('No MIA data to export. Process a transcript first.');
      return;
    }

    const data = {
      mia: miaOutput,
      exportedAt: new Date().toISOString(),
    };

    let content: string;
    let filename: string;
    let mimeType: string;

    switch (format) {
      case 'json':
        content = JSON.stringify(data, null, 2);
        filename = `mia_report_${Date.now()}.json`;
        mimeType = 'application/json';
        break;
      case 'markdown':
        content = generateMarkdown(miaOutput);
        filename = `mia_report_${Date.now()}.md`;
        mimeType = 'text/markdown';
        break;
      default:
        toast.error('Unsupported export format');
        return;
    }

    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);

    toast.success(`Exported as ${format.toUpperCase()}`);
  };

  const generateMarkdown = (mia: MIAResults): string => {
    const md = `# Meeting Intelligence Report

**Generated:** ${new Date().toLocaleString()}

## Meeting Summary

${mia.summary}

## Key Decisions

${mia.decisions.length > 0 
  ? mia.decisions.map((d, i) => 
      `${i + 1}. ${d.text}${d.speaker ? ` (${d.speaker})` : ''} - Confidence: ${(d.confidence * 100).toFixed(0)}%`
    ).join('\n')
  : 'No decisions identified.'
}

## Action Items

${mia.action_items.length > 0
  ? mia.action_items.map((a, i) => 
      `${i + 1}. **${a.action}**\n   - Owner: ${a.owner || 'Unassigned'}\n   - Due: ${a.due_date || 'Not specified'}\n   - Priority: ${a.priority.toUpperCase()}\n   - Confidence: ${(a.confidence * 100).toFixed(0)}%`
    ).join('\n\n')
  : 'No action items identified.'
}

## Identified Risks

${mia.risks.length > 0
  ? mia.risks.map((r, i) => 
      `${i + 1}. ${r.risk}${r.mentioned_by ? ` (mentioned by: ${r.mentioned_by})` : ''} - Confidence: ${(r.confidence * 100).toFixed(0)}%`
    ).join('\n')
  : 'No risks identified.'
}

## Meeting Participants

${mia.metadata.speakers.length > 0
  ? mia.metadata.speakers.join(', ')
  : 'No speakers identified.'
}

---

*Exported: ${new Date().toLocaleString()}*`;

    return md;
  };

  return (
    <div className="flex gap-2">
      <Button
        onClick={exportData}
        disabled={!miaOutput}
        className="gap-2"
        variant="default"
      >
        <Download className="w-4 h-4" />
        Export {format.toUpperCase()}
      </Button>
      <Button
        onClick={() => {
          if (!miaOutput) {
            toast.error('No data to preview');
            return;
          }
          const data = { mia: miaOutput };
          console.log('MIA Output:', data);
          toast.success('Data logged to console');
        }}
        variant="outline"
        disabled={!miaOutput}
        className="gap-2"
      >
        <FileJson className="w-4 h-4" />
        Preview
      </Button>
    </div>
  );
};
