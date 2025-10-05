import { useState } from 'react';
import { PaperSortAPI } from '../services/api';
import type { Topic } from '../types';
import './ReferenceManager.css';

interface ReferenceManagerProps {
  topics: Topic[];
}

export default function ReferenceManager({ topics }: ReferenceManagerProps) {
  const [selectedPaperIds, setSelectedPaperIds] = useState<Set<number>>(new Set());
  const [exporting, setExporting] = useState(false);
  const [enhanceOnline, setEnhanceOnline] = useState(true);
  const [validateEntries, setValidateEntries] = useState(true);

  const toggleSelectAll = (checked: boolean) => {
    if (checked) {
      const allIds = new Set<number>();
      topics.forEach(topic => {
        topic.papers.forEach(paper => {
          if (paper.id) allIds.add(paper.id);
        });
      });
      setSelectedPaperIds(allIds);
    } else {
      setSelectedPaperIds(new Set());
    }
  };

  const handleExportBibTeX = async () => {
    setExporting(true);

    try {
      const paperIds = selectedPaperIds.size > 0
        ? Array.from(selectedPaperIds)
        : undefined;

      const result = await PaperSortAPI.exportBibTeX(
        paperIds,
        enhanceOnline,
        validateEntries
      );

      if (result.success) {
        // Create a download link
        const blob = new Blob([result.content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'references.bib';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        alert(`Exported ${result.content.split('@').length - 1} references to references.bib`);
      }
    } catch (error) {
      console.error('Export failed:', error);
      alert('Failed to export BibTeX. Please try again.');
    } finally {
      setExporting(false);
    }
  };

  const totalPapers = topics.reduce((sum, topic) => sum + topic.count, 0);
  const selectedCount = selectedPaperIds.size;

  return (
    <div className="reference-manager">
      <div className="manager-header">
        <h2>📝 Reference Management</h2>
        <p>Export your organized papers to BibTeX format</p>
      </div>

      <div className="manager-options">
        <div className="selection-info">
          <label>
            <input
              type="checkbox"
              checked={selectedCount === totalPapers && totalPapers > 0}
              onChange={(e) => toggleSelectAll(e.target.checked)}
            />
            {selectedCount > 0
              ? `${selectedCount} paper(s) selected`
              : 'Select all papers'}
          </label>
        </div>

        <div className="export-options">
          <label>
            <input
              type="checkbox"
              checked={enhanceOnline}
              onChange={(e) => setEnhanceOnline(e.target.checked)}
            />
            Enhance metadata with online APIs
          </label>

          <label>
            <input
              type="checkbox"
              checked={validateEntries}
              onChange={(e) => setValidateEntries(e.target.checked)}
            />
            Validate BibTeX entries
          </label>
        </div>
      </div>

      <button
        onClick={handleExportBibTeX}
        disabled={exporting}
        className="btn-export-bibtex"
      >
        {exporting ? '⏳ Exporting...' : '📥 Export to BibTeX'}
      </button>

      <div className="export-info">
        <p>
          <strong>What gets exported:</strong>
        </p>
        <ul>
          <li>
            {selectedCount > 0
              ? `${selectedCount} selected papers`
              : `All ${totalPapers} papers from organized folders`}
          </li>
          {enhanceOnline && (
            <li>Metadata enhanced with CrossRef, arXiv, and Semantic Scholar</li>
          )}
          {validateEntries && (
            <li>Entries validated for required fields and special characters</li>
          )}
        </ul>
      </div>
    </div>
  );
}
