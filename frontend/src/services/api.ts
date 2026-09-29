import type { OrganizeRequest, MindMapRequest, MindMapResponse } from '../types';

const API_BASE_URL = 'http://127.0.0.1:8000/api';

export class PaperSortAPI {
  /**
   * Organize a folder of papers
   */
  static async organizeFolder(request: OrganizeRequest): Promise<{ task_id: string; message: string }> {
    const response = await fetch(`${API_BASE_URL}/organize/async`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`Failed to start organization: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Get task status
   */
  static async getTaskStatus(taskId: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/organize/status/${taskId}`);

    if (!response.ok) {
      throw new Error(`Failed to get task status: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Connect to WebSocket for real-time progress
   */
  static connectProgressWebSocket(
    taskId: string,
    onMessage: (data: any) => void,
    onError?: (error: Event) => void
  ): WebSocket {
    const ws = new WebSocket(`ws://127.0.0.1:8000/api/ws/organize/${taskId}`);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      onMessage(data);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      if (onError) onError(error);
    };

    return ws;
  }

  /**
   * Generate mind-map for a paper
   */
  static async generateMindMap(request: MindMapRequest): Promise<MindMapResponse> {
    const response = await fetch(`${API_BASE_URL}/mindmap/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      // Try to get detailed error message from response (e.g. "Cannot connect to Ollama").
      // Only JSON parsing may fail here -- the Error must be thrown outside the try,
      // otherwise the catch swallows it and the user only sees the status text.
      let detail: string | undefined;
      try {
        const errorData = await response.json();
        detail = errorData.detail;
      } catch (e) {
        // If parsing fails, use status text
      }
      throw new Error(detail || `Failed to generate mind-map: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Export papers to BibTeX
   */
  static async exportBibTeX(
    paperIds?: number[],
    enhanceOnline: boolean = true,
    validateEntries: boolean = true
  ): Promise<{ success: boolean; content: string; file_path: string }> {
    const response = await fetch(`${API_BASE_URL}/export/bibtex`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        paper_ids: paperIds,
        enhance_online: enhanceOnline,
        validate_entries: validateEntries,
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to export BibTeX: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Get folder structure (for loading existing organized folders)
   */
  static async getFolderStructure(folderPath: string): Promise<any> {
    const encodedPath = encodeURIComponent(folderPath);
    const response = await fetch(`${API_BASE_URL}/structure/${encodedPath}`);

    if (!response.ok) {
      throw new Error(`Failed to get folder structure: ${response.statusText}`);
    }

    return response.json();
  }
}
