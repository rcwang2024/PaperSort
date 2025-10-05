import type { ProgressUpdate } from '../types';
import './ProgressTracker.css';

interface ProgressTrackerProps {
  progress: ProgressUpdate | null;
}

export default function ProgressTracker({ progress }: ProgressTrackerProps) {
  if (!progress) {
    return (
      <div className="progress-tracker">
        <div className="progress-card">
          <h2>Initializing...</h2>
          <div className="spinner"></div>
        </div>
      </div>
    );
  }

  const getStatusEmoji = () => {
    switch (progress.status) {
      case 'starting':
        return '🚀';
      case 'processing':
        return '⚙️';
      case 'completed':
        return '✅';
      case 'failed':
        return '❌';
      default:
        return '⏳';
    }
  };

  const getStatusColor = () => {
    switch (progress.status) {
      case 'completed':
        return '#4caf50';
      case 'failed':
        return '#f44336';
      default:
        return '#2196f3';
    }
  };

  return (
    <div className="progress-tracker">
      <div className="progress-card">
        <div className="progress-header">
          <h2>
            {getStatusEmoji()} {progress.message}
          </h2>
        </div>

        <div className="progress-bar-container">
          <div
            className="progress-bar"
            style={{
              width: `${progress.progress}%`,
              backgroundColor: getStatusColor(),
            }}
          />
        </div>

        <div className="progress-percentage">
          {Math.round(progress.progress)}%
        </div>

        {progress.status === 'processing' && (
          <div className="progress-spinner">
            <div className="spinner"></div>
          </div>
        )}

        {progress.status === 'failed' && (
          <div className="error-info">
            <p>An error occurred during organization. Please check:</p>
            <ul>
              <li>The folder path is correct and accessible</li>
              <li>The backend server is running (http://127.0.0.1:8000)</li>
              <li>You have read/write permissions for the folder</li>
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
