import { useCallback, useState } from 'react';
import { Upload, FileText, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

interface FileUploadProps {
  onFilesSelected: (files: File[]) => void;
  acceptedFormats?: string[];
  maxSizeMB?: number;
}

export const FileUpload = ({
  onFilesSelected,
  acceptedFormats = ['.txt', '.json', '.srt'],
  maxSizeMB = 50,
}: FileUploadProps) => {
  const [isUploading, setIsUploading] = useState(false);

  const validateAndProcess = (files: File[]) => {
    if (isUploading) {
      toast.info('Upload in progress, please wait...');
      return;
    }

    const maxSize = maxSizeMB * 1024 * 1024;
    const validFiles = files.filter((file) => {
      const extension = '.' + file.name.split('.').pop()?.toLowerCase();
      if (!acceptedFormats.includes(extension)) {
        toast.error(`${file.name}: Unsupported format. Use ${acceptedFormats.join(', ')}`);
        return false;
      }
      if (file.size > maxSize) {
        toast.error(`${file.name}: File too large (max ${maxSizeMB}MB)`);
        return false;
      }
      return true;
    });

    if (validFiles.length > 0) {
      setIsUploading(true);
      // Call the parent handler which will handle the upload
      onFilesSelected(validFiles);
      // Reset uploading state after a short delay (parent will handle success/error)
      setTimeout(() => setIsUploading(false), 100);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      validateAndProcess(files);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const files = Array.from(e.target.files);
      validateAndProcess(files);
      // Reset input so same file can be selected again
      e.target.value = '';
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  return (
    <div
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      className={cn(
        'relative flex flex-col items-center justify-center',
        'border-2 border-dashed rounded-lg p-12',
        'border-workflow-node-border bg-workflow-node-bg/50',
        'hover:border-primary hover:bg-card/80 transition-all duration-300',
        'cursor-pointer group',
        isUploading && 'opacity-50 cursor-wait'
      )}
    >
      <input
        type="file"
        multiple={false}
        accept={acceptedFormats.join(',')}
        onChange={handleFileInput}
        disabled={isUploading}
        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
      />
      <div className="flex flex-col items-center gap-4 pointer-events-none">
        <div className="relative">
          {isUploading ? (
            <Loader2 className="w-12 h-12 text-primary animate-spin" />
          ) : (
            <>
              <Upload className="w-12 h-12 text-muted-foreground group-hover:text-primary transition-colors" />
              <div className="absolute inset-0 bg-primary/20 rounded-full blur-xl opacity-0 group-hover:opacity-100 transition-opacity" />
            </>
          )}
        </div>
        <div className="text-center">
          <p className="text-lg font-semibold text-foreground mb-1">
            {isUploading ? 'Uploading...' : 'Drop transcript file here'}
          </p>
          <p className="text-sm text-muted-foreground">
            {isUploading ? 'Please wait' : 'or click to browse'}
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <FileText className="w-4 h-4" />
          <span>Supports {acceptedFormats.join(', ').toUpperCase()} • Max {maxSizeMB}MB</span>
        </div>
      </div>
    </div>
  );
};
