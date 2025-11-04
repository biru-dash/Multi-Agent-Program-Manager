import { useState, useCallback, useEffect } from 'react';
import { FileUpload } from '@/components/FileUpload';
import { ConfigPanel } from '@/components/ConfigPanel';
import { WorkflowCanvas } from '@/components/WorkflowCanvas';
import { MIAOutput } from '@/components/MIAOutput';
import { ExportButtons } from '@/components/ExportButtons';
import { LogPanel, type LogEntry } from '@/components/LogPanel';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Play, RotateCcw } from 'lucide-react';
import { toast } from 'sonner';
import { AgentConfig, AgentState } from '@/types/agent';
import { miaService, type MIAResults } from '@/services/miaService';

const Index = () => {
  const [config, setConfig] = useState<AgentConfig>({
    modelStrategy: 'hybrid',
    preprocessing: 'advanced',
    confidenceThreshold: 75,
    outputFormat: 'json' as 'json' | 'markdown',
    workflowMode: 'full-pipeline', // Keep for type compatibility, but not used
  });

  const [agents, setAgents] = useState<AgentState[]>([
    { id: 'mia', name: 'Meeting Intelligence Agent', status: 'idle', progress: 0 },
  ]);
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [miaOutput, setMiaOutput] = useState<MIAResults | null>(null);
  const [uploadId, setUploadId] = useState<string | null>(null);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [backendStatus, setBackendStatus] = useState<{ reachable: boolean; status?: string; error?: string } | null>(null);

  // Helper function to add log entries
  const addLog = useCallback((level: LogEntry['level'], message: string) => {
    const logEntry: LogEntry = {
      id: `${Date.now()}-${Math.random()}`,
      timestamp: new Date(),
      level,
      message,
    };
    setLogs((prev) => [...prev, logEntry]);
  }, []);

  // Check backend health on mount
  useEffect(() => {
    const checkBackend = async () => {
      try {
        const health = await miaService.checkHealth();
        setBackendStatus({
          reachable: health.reachable,
          status: health.status,
          error: health.error,
        });
        
        if (health.reachable) {
          addLog('success', `Backend is reachable at ${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}`);
        } else {
          addLog('error', `Backend is not reachable: ${health.error}`);
          toast.error('Cannot connect to backend server. Please ensure it is running.');
        }
      } catch (error) {
        setBackendStatus({
          reachable: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    };

    checkBackend();
  }, []);

  const handleFilesSelected = async (files: File[]) => {
    if (files.length === 0) return;
    
    const file = files[0];
    addLog('info', `File selected: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`);
    
    // Upload the first file to backend
    try {
      addLog('info', 'Starting file upload to backend...');
      console.log('Uploading file:', file.name, 'Size:', file.size, 'bytes');
      
      const uploadResponse = await miaService.uploadFile(file);
      console.log('Upload successful:', uploadResponse);
      
      addLog('success', `File uploaded successfully: ${uploadResponse.filename}`);
      addLog('info', `Upload ID: ${uploadResponse.upload_id}`);
      
      setUploadId(uploadResponse.upload_id);
      setUploadedFiles(files);
      toast.success(`File uploaded: ${uploadResponse.filename}`);
    } catch (error) {
      console.error('Upload error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      
      addLog('error', `Upload failed: ${errorMessage}`);
      
      toast.error(`Upload failed: ${errorMessage}`);
      
      // Check if it's a connection error
      if (errorMessage.includes('Cannot connect to backend')) {
        addLog('warning', 'Backend server not running. Please start it with: cd backend && uvicorn app.main:app --reload');
        toast.error('Backend server not running. Start it with: cd backend && uvicorn app.main:app --reload');
      }
    }
  };

  const handleProcess = async () => {
    if (!uploadId) {
      addLog('warning', 'Cannot process: No file uploaded');
      toast.error('Please upload transcript files first');
      return;
    }

    setIsProcessing(true);
    setMiaOutput(null);

    addLog('info', 'Starting transcript processing...');
    addLog('info', `Model strategy: ${config.modelStrategy || 'hybrid'}`);
    addLog('info', `Preprocessing level: ${config.preprocessing || 'advanced'}`);

    // MIA Processing
    setAgents((prev) =>
      prev.map((a) =>
        a.id === 'mia' ? { ...a, status: 'processing', progress: 0 } : a
      )
    );

    try {
      // Start processing
      addLog('info', 'Sending processing request to backend...');
      const processResponse = await miaService.processTranscript(
        uploadId!,
        config.modelStrategy || 'hybrid',
        config.preprocessing || 'advanced'
      );
      
      setCurrentJobId(processResponse.job_id);
      addLog('success', `Processing job started. Job ID: ${processResponse.job_id}`);
      addLog('info', 'Polling for status updates...');

      // Poll for status updates
      await miaService.pollJobStatus(
        processResponse.job_id,
        (status) => {
          // Log progress updates
          if (status.progress > 0) {
            addLog('info', `Processing progress: ${status.progress}%`);
          }
          
          if (status.status === 'processing' && status.message) {
            addLog('info', status.message);
          }
          
          setAgents((prev) =>
            prev.map((a) =>
              a.id === 'mia'
                ? { 
                    ...a, 
                    progress: status.progress, 
                    status: status.status === 'completed' 
                      ? 'success' 
                      : status.status === 'failed' 
                        ? 'error' 
                        : 'processing',
                    error: status.error
                  }
                : a
            )
          );
        }
      );

      addLog('success', 'Processing completed successfully');
      addLog('info', 'Fetching results...');

      // Get results
      const results = await miaService.getResults(processResponse.job_id);
      setMiaOutput(results);
      
      addLog('success', 'Results retrieved successfully');
      addLog('info', `Found ${results.decisions.length} decisions, ${results.action_items.length} action items, ${results.risks.length} risks`);
      
      toast.success('MIA processing complete!');
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Processing failed';
      addLog('error', `Processing failed: ${errorMessage}`);
      
      setAgents((prev) =>
        prev.map((a) =>
          a.id === 'mia' 
            ? { 
                ...a, 
                status: 'error', 
                error: errorMessage
              } 
            : a
        )
      );
      toast.error(`MIA processing failed: ${errorMessage}`);
    } finally {
      setIsProcessing(false);
      addLog('info', 'Processing finished');
    }
  };

  const handleReset = () => {
    setAgents([{ id: 'mia', name: 'Meeting Intelligence Agent', status: 'idle', progress: 0 }]);
    setUploadedFiles([]);
    setUploadId(null);
    setCurrentJobId(null);
    setMiaOutput(null);
    setIsProcessing(false);
    setLogs([]);
    addLog('info', 'Workflow reset');
    toast.info('Workflow reset');
  };

  const handleClearLogs = () => {
    setLogs([]);
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card/30 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold bg-gradient-primary bg-clip-text text-transparent">
                Meeting Intelligence Agent (MIA)
              </h1>
              <p className="text-sm text-muted-foreground">
                Sprint 1: Extract insights from meeting transcripts
              </p>
            </div>
            <div className="flex items-center gap-3">
              <ExportButtons
                miaOutput={miaOutput}
                reaOutput={null}
                format={config.outputFormat}
                jobId={currentJobId}
              />
              <Button
                onClick={handleProcess}
                disabled={isProcessing || uploadedFiles.length === 0}
                className="gap-2"
              >
                <Play className="w-4 h-4" />
                Process Transcript
              </Button>
              <Button onClick={handleReset} variant="outline" className="gap-2">
                <RotateCcw className="w-4 h-4" />
                Reset
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Layout */}
      <div className="container mx-auto p-6">
        <div className="grid grid-cols-12 gap-6">
          {/* Left Sidebar - Config */}
          <div className="col-span-3 space-y-6">
            <ConfigPanel config={config} onConfigChange={setConfig} />
            <Card className="p-4 border-border bg-card/50">
              <h3 className="font-semibold text-foreground mb-3">Upload Transcript</h3>
              <FileUpload onFilesSelected={handleFilesSelected} />
              {uploadedFiles.length > 0 && (
                <div className="mt-3 text-xs text-muted-foreground">
                  {uploadedFiles.length} file(s) ready
                </div>
              )}
            </Card>
            {/* Activity Log */}
            <LogPanel logs={logs} onClear={handleClearLogs} />
          </div>

          {/* Center - Workflow & Output */}
          <div className="col-span-9 space-y-6">
            {/* Workflow Canvas */}
            <Card className="border-border bg-card/30 backdrop-blur-sm h-[300px]">
              <WorkflowCanvas agents={agents} workflowMode="full-pipeline" />
            </Card>

            {/* MIA Output */}
            <Card className="border-border bg-card/50 backdrop-blur-sm">
              <div className="p-6">
                <h2 className="text-xl font-semibold text-foreground mb-4">Meeting Intelligence Results</h2>
                <MIAOutput output={miaOutput} />
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Index;
