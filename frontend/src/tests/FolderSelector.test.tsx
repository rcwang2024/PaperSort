/**
 * Tests for FolderSelector component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import FolderSelector from '../components/FolderSelector'
import { PaperSortAPI } from '../services/api'

// Mock the API
vi.mock('../services/api', () => ({
  PaperSortAPI: {
    organizeFolder: vi.fn(),
    connectProgressWebSocket: vi.fn(),
  },
}))

describe('FolderSelector', () => {
  const mockOnFolderSelected = vi.fn()
  const mockOnOrganizationStart = vi.fn()
  const mockOnProgressUpdate = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the component', () => {
    render(
      <FolderSelector
        onFolderSelected={mockOnFolderSelected}
        onOrganizationStart={mockOnOrganizationStart}
        onProgressUpdate={mockOnProgressUpdate}
      />
    )

    expect(screen.getByText('Select Papers Folder')).toBeInTheDocument()
    expect(screen.getByText('📁 Choose Folder')).toBeInTheDocument()
    expect(screen.getByText('🚀 Organize Papers')).toBeInTheDocument()
  })

  it('disables organize button when no folder is selected', () => {
    render(
      <FolderSelector
        onFolderSelected={mockOnFolderSelected}
        onOrganizationStart={mockOnOrganizationStart}
        onProgressUpdate={mockOnProgressUpdate}
      />
    )

    const organizeButton = screen.getByText('🚀 Organize Papers')
    expect(organizeButton).toBeDisabled()
  })

  it('shows error when trying to organize without folder', async () => {
    render(
      <FolderSelector
        onFolderSelected={mockOnFolderSelected}
        onOrganizationStart={mockOnOrganizationStart}
        onProgressUpdate={mockOnProgressUpdate}
      />
    )

    const organizeButton = screen.getByText('🚀 Organize Papers')
    expect(organizeButton).toBeDisabled()
  })

  it('allows switching between copy and move modes', async () => {
    const user = userEvent.setup()
    render(
      <FolderSelector
        onFolderSelected={mockOnFolderSelected}
        onOrganizationStart={mockOnOrganizationStart}
        onProgressUpdate={mockOnProgressUpdate}
      />
    )

    const copyRadio = screen.getByLabelText(/copy files/i)
    const moveRadio = screen.getByLabelText(/move files/i)

    // Copy should be selected by default
    expect(copyRadio).toBeChecked()
    expect(moveRadio).not.toBeChecked()

    // Switch to move mode
    await user.click(moveRadio)
    expect(moveRadio).toBeChecked()
    expect(copyRadio).not.toBeChecked()
  })

  it('accepts number of topics input', async () => {
    const user = userEvent.setup()
    render(
      <FolderSelector
        onFolderSelected={mockOnFolderSelected}
        onOrganizationStart={mockOnOrganizationStart}
        onProgressUpdate={mockOnProgressUpdate}
      />
    )

    const numTopicsInput = screen.getByPlaceholderText(/^Auto/)
    await user.type(numTopicsInput, '5')

    expect(numTopicsInput).toHaveValue(5)
  })

  it('accepts custom topics input', async () => {
    const user = userEvent.setup()
    render(
      <FolderSelector
        onFolderSelected={mockOnFolderSelected}
        onOrganizationStart={mockOnOrganizationStart}
        onProgressUpdate={mockOnProgressUpdate}
      />
    )

    const customTopicsInput = screen.getByPlaceholderText(/Machine Learning/i)
    await user.type(customTopicsInput, 'AI, NLP, Vision')

    expect(customTopicsInput).toHaveValue('AI, NLP, Vision')
  })

  it('shows selected folder path', () => {
    render(
      <FolderSelector
        onFolderSelected={mockOnFolderSelected}
        onOrganizationStart={mockOnOrganizationStart}
        onProgressUpdate={mockOnProgressUpdate}
      />
    )

    // Simulate folder selection
    const selectButton = screen.getByText('📁 Choose Folder')
    fireEvent.click(selectButton)
  })

  it('calls API when organize button is clicked with valid folder', async () => {
    const mockTaskId = 'test-task-123'
    const mockWs = {
      close: vi.fn(),
      onmessage: null,
      onerror: null,
    } as any

    vi.mocked(PaperSortAPI.organizeFolder).mockResolvedValue({
      task_id: mockTaskId,
      message: 'Started',
    })
    vi.mocked(PaperSortAPI.connectProgressWebSocket).mockReturnValue(mockWs)

    // The test setup provides window.electron, so the component uses the native picker
    vi.mocked(window.electron.selectFolder).mockResolvedValue('/test/folder')

    render(
      <FolderSelector
        onFolderSelected={mockOnFolderSelected}
        onOrganizationStart={mockOnOrganizationStart}
        onProgressUpdate={mockOnProgressUpdate}
      />
    )

    // Select folder
    const selectButton = screen.getByText('📁 Choose Folder')
    fireEvent.click(selectButton)

    await waitFor(() => {
      expect(mockOnFolderSelected).toHaveBeenCalledWith('/test/folder')
    })

    // Organize
    const organizeButton = screen.getByText('🚀 Organize Papers')
    fireEvent.click(organizeButton)

    await waitFor(() => {
      expect(mockOnOrganizationStart).toHaveBeenCalled()
      expect(PaperSortAPI.organizeFolder).toHaveBeenCalledWith(
        expect.objectContaining({
          folder_path: '/test/folder',
          copy_mode: true,
        })
      )
    })
  })

  it('shows error when API call fails', async () => {
    vi.mocked(PaperSortAPI.organizeFolder).mockRejectedValue(
      new Error('API Error')
    )

    // The test setup provides window.electron, so the component uses the native picker
    vi.mocked(window.electron.selectFolder).mockResolvedValue('/test/folder')

    render(
      <FolderSelector
        onFolderSelected={mockOnFolderSelected}
        onOrganizationStart={mockOnOrganizationStart}
        onProgressUpdate={mockOnProgressUpdate}
      />
    )

    // Select folder
    const selectButton = screen.getByText('📁 Choose Folder')
    fireEvent.click(selectButton)

    await waitFor(() => {
      expect(screen.getByText(/Selected:/)).toBeInTheDocument()
    })

    // Try to organize
    const organizeButton = screen.getByText('🚀 Organize Papers')
    fireEvent.click(organizeButton)

    await waitFor(() => {
      expect(screen.getByText(/API Error/)).toBeInTheDocument()
    })
  })
})
