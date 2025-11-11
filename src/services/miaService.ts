/** API service for Meeting Intelligence Agent backend */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export interface UploadResponse {
  upload_id: string;
  filename: string;
  size_mb: number;
  source?: string;
}

export interface TranscriptFile {
  filename: string;
  size_mb: number;
  path: string;
}

export interface TranscriptListResponse {
  files: TranscriptFile[];
}

export interface JobStatus {
  status: 'processing' | 'completed' | 'failed';
  progress: number;
  message: string;
  error?: string;
  elapsed?: number;
  eta?: number;
  estimated_total?: number;
  actual_time?: number;
}

export interface MIAResults {
  summary: string;
  decisions: Array<{
    text: string;
    speaker: string | null;
    timestamp: string | null;
    confidence: number;
  }>;
  action_items: Array<{
    action: string;
    owner: string | null;
    due_date: string | null;
    priority: string;
    confidence: number;
  }>;
  risks: Array<{
    risk: string;
    category?: string;
    priority?: string;
    impact?: string | null;
    mitigation?: string | null;
    owner?: string | null;
    mentioned_by: string | null;
    confidence: number;
  }>;
  metadata: {
    speakers: string[];
    segment_count: number;
    extracted_at: string;
  };
  preprocessing_metadata?: Record<string, any>;
}

class MIAService {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * List available transcript files from meeting_transcripts folder
   */
  async listTranscripts(): Promise<TranscriptFile[]> {
    try {
      const response = await fetch(`${this.baseUrl}/api/transcripts`);
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to list transcripts');
      }
      
      const data: TranscriptListResponse = await response.json();
      return data.files;
    } catch (error) {
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error(
          `Cannot connect to backend at ${this.baseUrl}. ` +
          `Make sure the backend server is running on port 8000.`
        );
      }
      throw error;
    }
  }

  /**
   * Select a transcript file from meeting_transcripts folder
   */
  async selectTranscript(filename: string): Promise<UploadResponse> {
    try {
      const response = await fetch(
        `${this.baseUrl}/api/transcripts/select?filename=${encodeURIComponent(filename)}`,
        {
          method: 'POST',
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to select transcript');
      }

      return response.json();
    } catch (error) {
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error(
          `Cannot connect to backend at ${this.baseUrl}. ` +
          `Make sure the backend server is running on port 8000.`
        );
      }
      throw error;
    }
  }

  /**
   * Upload a transcript file
   */
  async uploadFile(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${this.baseUrl}/api/upload`, {
        method: 'POST',
        body: formData,
        // Don't set Content-Type - browser will set it with boundary for FormData
      });

      if (!response.ok) {
        let errorMessage = `Upload failed with status ${response.status}`;
        
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.message || errorMessage;
        } catch {
          // If response is not JSON, try text
          try {
            const errorText = await response.text();
            if (errorText) {
              errorMessage = errorText;
            }
          } catch {
            // Use default error message
          }
        }
        
        throw new Error(errorMessage);
      }

      return await response.json();
    } catch (error) {
      // Handle network errors, CORS errors, etc.
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error(
          `Cannot connect to backend at ${this.baseUrl}. ` +
          `Make sure the backend server is running on port 8000. ` +
          `Error: ${error.message}`
        );
      }
      throw error;
    }
  }

  /**
   * Process uploaded transcript
   */
  async processTranscript(
    uploadId: string,
    modelStrategy: 'local' | 'remote' | 'hybrid' | 'ollama' = 'hybrid',
    preprocessing: 'basic' | 'advanced' = 'advanced'
  ): Promise<{ job_id: string; status: string; message: string }> {
    const response = await fetch(
      `${this.baseUrl}/api/process/${uploadId}?model_strategy=${modelStrategy}&preprocessing=${preprocessing}`,
      {
        method: 'POST',
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Processing failed');
    }

    return response.json();
  }

  /**
   * Get job status
   */
  async getJobStatus(jobId: string): Promise<JobStatus> {
    const response = await fetch(`${this.baseUrl}/api/status/${jobId}`);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get job status');
    }

    return response.json();
  }

  /**
   * Get processing results
   */
  async getResults(jobId: string): Promise<MIAResults> {
    const response = await fetch(`${this.baseUrl}/api/results/${jobId}`);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get results');
    }

    return response.json();
  }

  /**
   * Poll job status until completion
   */
  async pollJobStatus(
    jobId: string,
    onProgress?: (status: JobStatus) => void,
    pollInterval: number = 1000
  ): Promise<JobStatus> {
    return new Promise((resolve, reject) => {
      const poll = async () => {
        try {
          const status = await this.getJobStatus(jobId);
          
          if (onProgress) {
            onProgress(status);
          }

          if (status.status === 'completed' || status.status === 'failed') {
            resolve(status);
          } else {
            setTimeout(poll, pollInterval);
          }
        } catch (error) {
          reject(error);
        }
      };

      poll();
    });
  }

  /**
   * Export results as file
   */
  async exportResults(jobId: string, format: 'json' | 'md' = 'json'): Promise<Blob> {
    const response = await fetch(`${this.baseUrl}/api/export/${jobId}?format=${format}`);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Export failed');
    }

    return response.blob();
  }

  /**
   * Download exported file
   */
  downloadFile(blob: Blob, filename: string): void {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  }
}

export const miaService = new MIAService();
