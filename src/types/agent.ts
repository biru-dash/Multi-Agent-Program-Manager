export type AgentStatus = 'idle' | 'processing' | 'success' | 'error';

export type WorkflowMode = 'full-pipeline' | 'direct-rea';

export interface MIAOutput {
  summary: string;
  decisions: string[];
  actions: string[];
  risks: string[];
  owners: string[];
}

export interface UserStory {
  id: string;
  title: string;
  description: string;
  acceptanceCriteria: string[];
  priority: 'low' | 'medium' | 'high';
}

export interface REAOutput {
  userStories: UserStory[];
  priorities: string[];
}

export interface REAInput {
  source: 'mia' | 'file';
  miaOutput?: MIAOutput;
  files?: File[];
}

export interface AgentConfig {
  llmModel?: string;
  modelStrategy?: 'local' | 'remote' | 'hybrid' | 'ollama';
  preprocessing?: 'basic' | 'advanced';
  confidenceThreshold: number;
  outputFormat: 'json' | 'markdown';
  workflowMode: WorkflowMode;
  // Advanced Ollama parameters
  temperature?: number;
  maxTokens?: number;
  topP?: number;
  contextChunking?: boolean;
  chunkSize?: number;
  extractionMode?: 'comprehensive' | 'focused' | 'creative';
}

export interface AgentState {
  id: string;
  name: string;
  status: AgentStatus;
  progress: number;
  error?: string;
  message?: string;
  elapsed?: number;
  eta?: number;
  estimatedTotal?: number;
}
