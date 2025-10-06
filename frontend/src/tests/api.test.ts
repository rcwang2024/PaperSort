/**
 * Tests for PaperSortAPI service
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { PaperSortAPI } from '../services/api'

// Mock global fetch
global.fetch = vi.fn()

describe('PaperSortAPI', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('organizeFolder', () => {
    it('calls the correct endpoint with request data', async () => {
      const mockResponse = {
        task_id: 'test-123',
        message: 'Started',
      }

      vi.mocked(fetch).mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const request = {
        folder_path: '/test/path',
        copy_mode: true,
        enhance_metadata: false,
      }

      const result = await PaperSortAPI.organizeFolder(request)

      expect(fetch).toHaveBeenCalledWith(
        'http://127.0.0.1:8000/api/organize/async',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(request),
        })
      )
      expect(result).toEqual(mockResponse)
    })

    it('throws error when request fails', async () => {
      vi.mocked(fetch).mockResolvedValue({
        ok: false,
        statusText: 'Bad Request',
      } as Response)

      await expect(
        PaperSortAPI.organizeFolder({
          folder_path: '/test/path',
          copy_mode: true,
        })
      ).rejects.toThrow('Failed to start organization')
    })
  })

  describe('getTaskStatus', () => {
    it('retrieves task status successfully', async () => {
      const mockStatus = {
        status: 'processing',
        progress: 50,
        message: 'Processing papers...',
      }

      vi.mocked(fetch).mockResolvedValue({
        ok: true,
        json: async () => mockStatus,
      } as Response)

      const result = await PaperSortAPI.getTaskStatus('test-123')

      expect(fetch).toHaveBeenCalledWith(
        'http://127.0.0.1:8000/api/organize/status/test-123'
      )
      expect(result).toEqual(mockStatus)
    })

    it('throws error when task not found', async () => {
      vi.mocked(fetch).mockResolvedValue({
        ok: false,
        statusText: 'Not Found',
      } as Response)

      await expect(PaperSortAPI.getTaskStatus('invalid-id')).rejects.toThrow(
        'Failed to get task status'
      )
    })
  })

  describe('generateMindMap', () => {
    it('generates mindmap successfully', async () => {
      const mockResponse = {
        paper_title: 'Test Paper',
        root_node: { name: 'Test', children: [] },
        generation_time: 1.5,
      }

      vi.mocked(fetch).mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const request = {
        paper_title: 'Test Paper',
        abstract: 'Test abstract',
        full_text: 'Test content',
        include_methodology: true,
        include_results: true,
      }

      const result = await PaperSortAPI.generateMindMap(request)

      expect(fetch).toHaveBeenCalledWith(
        'http://127.0.0.1:8000/api/mindmap/generate',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(request),
        })
      )
      expect(result).toEqual(mockResponse)
    })

    it('extracts detailed error message from response', async () => {
      const errorDetail = 'Insufficient text content'

      vi.mocked(fetch).mockResolvedValue({
        ok: false,
        statusText: 'Bad Request',
        json: async () => ({ detail: errorDetail }),
      } as Response)

      await expect(
        PaperSortAPI.generateMindMap({
          paper_title: 'Test',
          abstract: 'Short',
        })
      ).rejects.toThrow(errorDetail)
    })
  })

  describe('exportBibTeX', () => {
    it('exports BibTeX successfully', async () => {
      const mockResponse = {
        success: true,
        content: '@article{test}',
        file_path: '/path/to/file.bib',
      }

      vi.mocked(fetch).mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const result = await PaperSortAPI.exportBibTeX([1, 2, 3], true, true)

      expect(fetch).toHaveBeenCalledWith(
        'http://127.0.0.1:8000/api/export/bibtex',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            paper_ids: [1, 2, 3],
            enhance_online: true,
            validate_entries: true,
          }),
        })
      )
      expect(result).toEqual(mockResponse)
    })
  })

  describe('getFolderStructure', () => {
    it('retrieves folder structure successfully', async () => {
      const mockStructure = {
        folder: '/test/path',
        topics: { ML: [], CV: [] },
        total_papers: 0,
      }

      vi.mocked(fetch).mockResolvedValue({
        ok: true,
        json: async () => mockStructure,
      } as Response)

      const result = await PaperSortAPI.getFolderStructure('/test/path')

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/structure/')
      )
      expect(result).toEqual(mockStructure)
    })

    it('encodes folder path correctly', async () => {
      vi.mocked(fetch).mockResolvedValue({
        ok: true,
        json: async () => ({}),
      } as Response)

      await PaperSortAPI.getFolderStructure('/test/path with spaces')

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining(encodeURIComponent('/test/path with spaces'))
      )
    })
  })

  describe('connectProgressWebSocket', () => {
    it('creates WebSocket with correct URL', () => {
      const mockOnMessage = vi.fn()
      const taskId = 'test-123'

      // Mock WebSocket
      global.WebSocket = vi.fn().mockImplementation(() => ({
        onmessage: null,
        onerror: null,
        close: vi.fn(),
      })) as any

      const ws = PaperSortAPI.connectProgressWebSocket(taskId, mockOnMessage)

      expect(WebSocket).toHaveBeenCalledWith(
        `ws://127.0.0.1:8000/api/ws/organize/${taskId}`
      )
    })

    it('parses incoming messages', () => {
      const mockOnMessage = vi.fn()
      const mockData = { status: 'processing', progress: 50 }

      let messageHandler: ((event: MessageEvent) => void) | null = null

      global.WebSocket = vi.fn().mockImplementation(() => ({
        set onmessage(handler) {
          messageHandler = handler
        },
        onerror: null,
        close: vi.fn(),
      })) as any

      PaperSortAPI.connectProgressWebSocket('test-123', mockOnMessage)

      // Simulate message
      if (messageHandler) {
        messageHandler({
          data: JSON.stringify(mockData),
        } as MessageEvent)
      }

      expect(mockOnMessage).toHaveBeenCalledWith(mockData)
    })
  })
})
