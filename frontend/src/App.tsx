import { useState } from 'react';
import FolderSelector from './components/FolderSelector';
import TopicList from './components/TopicList';
import ProgressTracker from './components/ProgressTracker';
import ReferenceManager from './components/ReferenceManager';
import type { Topic, ProgressUpdate } from './types';
import './App.css';

function App() {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState<ProgressUpdate | null>(null);
  const [selectedFolder, setSelectedFolder] = useState<string>('');

  const handleOrganizationComplete = (results: any) => {
    // Convert backend response to Topic array
    const topicArray: Topic[] = Object.entries(results.topics).map(([name, papers]) => ({
      name,
      count: (papers as any[]).length,
      papers: papers as any[],
    }));

    setTopics(topicArray);
    setIsProcessing(false);
  };

  const handleProgressUpdate = (update: ProgressUpdate) => {
    setProgress(update);

    if (update.status === 'completed' && update.results) {
      handleOrganizationComplete(update.results);
    } else if (update.status === 'failed') {
      setIsProcessing(false);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>📚 PaperSort v2.0</h1>
        <p>Organize, visualize, and manage your scientific papers</p>
      </header>

      <main className="app-main">
        {!isProcessing && topics.length === 0 && (
          <FolderSelector
            onFolderSelected={setSelectedFolder}
            onOrganizationStart={() => setIsProcessing(true)}
            onProgressUpdate={handleProgressUpdate}
          />
        )}

        {isProcessing && (
          <ProgressTracker progress={progress} />
        )}

        {!isProcessing && topics.length > 0 && (
          <div className="results-container">
            <div className="results-header">
              <h2>📂 Organized Papers</h2>
              <p className="folder-path">{selectedFolder}</p>
              <p className="stats">
                {topics.length} topics • {topics.reduce((sum, t) => sum + t.count, 0)} papers
              </p>
            </div>

            <TopicList topics={topics} />

            <ReferenceManager topics={topics} />
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
