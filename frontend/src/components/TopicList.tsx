import { useState } from 'react';
import { PaperSortAPI } from '../services/api';
import MindMapWindow from './MindMapWindow';
import type { Topic, Paper } from '../types';
import './TopicList.css';

interface TopicListProps {
  topics: Topic[];
}

export default function TopicList({ topics }: TopicListProps) {
  const [expandedTopics, setExpandedTopics] = useState<Set<string>>(new Set());
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null);
  const [showMindMap, setShowMindMap] = useState(false);
  const [mindMapSVG, setMindMapSVG] = useState('');
  const [mindMapSummary, setMindMapSummary] = useState('');
  const [loadingMindMap, setLoadingMindMap] = useState(false);

  const toggleTopic = (topicName: string) => {
    const newExpanded = new Set(expandedTopics);
    if (newExpanded.has(topicName)) {
      newExpanded.delete(topicName);
    } else {
      newExpanded.add(topicName);
    }
    setExpandedTopics(newExpanded);
  };

  const handleGenerateMindMap = async (paper: Paper) => {
    setSelectedPaper(paper);
    setLoadingMindMap(true);

    try {
      const response = await PaperSortAPI.generateMindMap({
        paper_id: paper.id,
        paper_title: paper.title,
        abstract: paper.abstract || '',
        full_text: paper.full_text || '',
        include_methodology: true,
        include_results: true,
        max_depth: 3,
      });

      if (response.svg_data) {
        setMindMapSVG(response.svg_data);
        setMindMapSummary(response.summary || '');
        setShowMindMap(true);
      }
    } catch (error: any) {
      console.error('Failed to generate mind-map:', error);

      // Show the detailed error message from backend
      const errorMessage = error.message || 'Failed to generate mind-map. Please try again.';
      alert(`Mind-map generation failed:\n\n${errorMessage}`);
    } finally{
      setLoadingMindMap(false);
    }
  };

  return (
    <div className="topic-list">
      {topics.map((topic) => (
        <div key={topic.name} className="topic-card">
          <div
            className="topic-header"
            onClick={() => toggleTopic(topic.name)}
          >
            <h3>
              <span className="toggle-icon">
                {expandedTopics.has(topic.name) ? '▼' : '▶'}
              </span>
              {topic.name}
            </h3>
            <span className="topic-count">{topic.count} papers</span>
          </div>

          {expandedTopics.has(topic.name) && (
            <div className="topic-content">
              <div className="papers-section">
                <h4>Papers in this topic:</h4>
                {topic.papers.length > 0 && topic.papers[0].path && (
                  <div className="folder-path">
                    📁 Folder: {topic.papers[0].path.substring(0, topic.papers[0].path.lastIndexOf('/'))}
                  </div>
                )}
                <div className="papers-list">
                  {topic.papers.map((paper, idx) => (
                    <div key={idx} className="paper-item">
                      <div className="paper-info">
                        <div className="paper-title">{paper.title}</div>
                        <div className="paper-meta">
                          {paper.authors?.join(', ')} {paper.year && `(${paper.year})`}
                        </div>
                        {paper.abstract && (
                          <div className="paper-abstract">{paper.abstract}</div>
                        )}
                        {paper.path && (
                          <div className="paper-filename">
                            📄 {paper.path.substring(paper.path.lastIndexOf('/') + 1)}
                          </div>
                        )}
                      </div>
                      <div className="paper-actions">
                        <button
                          onClick={() => handleGenerateMindMap(paper)}
                          disabled={loadingMindMap}
                          className="btn-mindmap"
                          title="Generate mind-map visualization"
                        >
                          {loadingMindMap && selectedPaper?.id === paper.id
                            ? '⏳ Generating...'
                            : '🗺️ Mind-Map'}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      ))}

      {showMindMap && selectedPaper && (
        <MindMapWindow
          paper={selectedPaper}
          svgData={mindMapSVG}
          summary={mindMapSummary}
          onClose={() => {
            setShowMindMap(false);
            setSelectedPaper(null);
            setMindMapSVG('');
            setMindMapSummary('');
          }}
        />
      )}
    </div>
  );
}
