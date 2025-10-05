import { useEffect, useRef } from 'react';
import type { Paper } from '../types';
import './MindMapWindow.css';

interface MindMapWindowProps {
  paper: Paper;
  svgData: string;
  summary?: string;
  onClose: () => void;
}

export default function MindMapWindow({ paper, svgData, summary, onClose }: MindMapWindowProps) {
  const svgContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (svgContainerRef.current && svgData) {
      svgContainerRef.current.innerHTML = svgData;
    }
  }, [svgData]);

  const handleExportSVG = () => {
    // Create a blob from the SVG data
    const blob = new Blob([svgData], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);

    // Create a download link and trigger it
    const a = document.createElement('a');
    a.href = url;
    a.download = `${paper.title.replace(/[^a-zA-Z0-9]/g, '_')}_mindmap.svg`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="mindmap-overlay">
      <div className="mindmap-window">
        <div className="mindmap-header">
          <div className="mindmap-title">
            <h2>🗺️ Mind-Map: {paper.title}</h2>
            <p className="paper-authors">
              {paper.authors?.join(', ')} {paper.year && `(${paper.year})`}
            </p>
          </div>
          <div className="mindmap-actions">
            <button onClick={handleExportSVG} className="btn-export">
              💾 Export SVG
            </button>
            <button onClick={onClose} className="btn-close">
              ✕
            </button>
          </div>
        </div>

        {summary && (
          <div className="mindmap-summary">
            <h3>📄 Comprehensive Summary</h3>
            <div className="summary-content">
              {summary.split('\n').map((paragraph, idx) => (
                <p key={idx}>{paragraph}</p>
              ))}
            </div>
          </div>
        )}

        <div className="mindmap-content" ref={svgContainerRef}>
          {!svgData && <div className="loading">Loading mind-map...</div>}
        </div>

        <div className="mindmap-footer">
          <p className="help-text">
            Use mouse wheel to zoom • Click and drag to pan
          </p>
        </div>
      </div>
    </div>
  );
}
