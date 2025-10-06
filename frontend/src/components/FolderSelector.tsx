import { useState } from 'react';
import { PaperSortAPI } from '../services/api';
import type { OrganizeRequest, ProgressUpdate } from '../types';
import './FolderSelector.css';

interface FolderSelectorProps {
  onFolderSelected: (path: string) => void;
  onOrganizationStart: () => void;
  onProgressUpdate: (update: ProgressUpdate) => void;
}

export default function FolderSelector({
  onFolderSelected,
  onOrganizationStart,
  onProgressUpdate,
}: FolderSelectorProps) {
  const [folderPath, setFolderPath] = useState('');
  const [copyMode, setCopyMode] = useState(true);
  const [numTopics, setNumTopics] = useState<number | undefined>(undefined);
  const [customTopics, setCustomTopics] = useState('');
  const [error, setError] = useState('');

  const handleFolderSelect = async () => {
    try {
      // Check if running in Electron
      if (window.electron && window.electron.selectFolder) {
        const path = await window.electron.selectFolder();
        if (path) {
          setFolderPath(path);
          onFolderSelected(path);
        }
      } else {
        // Fallback for web/development
        const path = prompt('Enter the folder path containing your papers:');
        if (path) {
          setFolderPath(path);
          onFolderSelected(path);
        }
      }
    } catch (err) {
      console.error('Folder selection error:', err);
      setError('Failed to open folder picker');
    }
  };

  const handleOrganize = async () => {
    if (!folderPath) {
      setError('Please select a folder first');
      return;
    }

    setError('');

    const request: OrganizeRequest = {
      folder_path: folderPath,
      num_topics: numTopics,
      custom_topics: customTopics ? customTopics.split(',').map(t => t.trim()) : undefined,
      copy_mode: copyMode,
      enhance_metadata: false,
    };

    try {
      onOrganizationStart();

      // Start async organization
      const { task_id } = await PaperSortAPI.organizeFolder(request);

      // Connect WebSocket for progress updates
      const ws = PaperSortAPI.connectProgressWebSocket(
        task_id,
        (data) => {
          onProgressUpdate(data);

          // Close WebSocket when done
          if (data.status === 'completed' || data.status === 'failed') {
            ws.close();
          }
        },
        (error) => {
          console.error('WebSocket error:', error);
          setError('Connection error. Please check if the backend is running.');
        }
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Organization failed');
      onProgressUpdate({
        status: 'failed',
        progress: 0,
        message: 'Organization failed',
      });
    }
  };

  return (
    <div className="folder-selector">
      <div className="selector-card">
        <h2>Select Papers Folder</h2>

        <div className="folder-input-group">
          <button onClick={handleFolderSelect} className="btn-primary">
            📁 Choose Folder
          </button>
          {folderPath && (
            <div className="selected-folder">
              <strong>Selected:</strong> {folderPath}
            </div>
          )}
        </div>

        <div className="options-group">
          <h3>Organization Options</h3>

          <div className="option">
            <label>
              <input
                type="radio"
                checked={copyMode}
                onChange={() => setCopyMode(true)}
              />
              Copy files (keep originals)
            </label>
          </div>

          <div className="option">
            <label>
              <input
                type="radio"
                checked={!copyMode}
                onChange={() => setCopyMode(false)}
              />
              Move files (remove originals)
            </label>
          </div>

          <div className="option">
            <label>
              Number of topics (leave empty for auto-detect, max 15):
              <input
                type="number"
                min="2"
                max="15"
                value={numTopics || ''}
                onChange={(e) => {
                  const val = e.target.value ? parseInt(e.target.value) : undefined;
                  // Enforce max of 15
                  setNumTopics(val && val > 15 ? 15 : val);
                }}
                placeholder="Auto (max 15)"
              />
            </label>
          </div>

          <div className="option">
            <label>
              Custom topics (comma-separated, max 15):
              <input
                type="text"
                value={customTopics}
                onChange={(e) => setCustomTopics(e.target.value)}
                placeholder="e.g., Machine Learning, Computer Vision"
              />
            </label>
            <small style={{ color: '#666', fontSize: '0.85em' }}>
              Note: Maximum 15 topics to keep folders organized
            </small>
          </div>
        </div>

        {error && (
          <div className="error-message">
            ⚠️ {error}
          </div>
        )}

        <button
          onClick={handleOrganize}
          disabled={!folderPath}
          className="btn-organize"
        >
          🚀 Organize Papers
        </button>

        <div className="help-text">
          <p>Papers will be renamed to: <code>[Year] Title - Author.pdf</code></p>
          <p>Organized into topic-based subfolders (max 15 topics)</p>
        </div>
      </div>
    </div>
  );
}
