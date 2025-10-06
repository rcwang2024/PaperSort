/**
 * Vitest test setup file
 */

import '@testing-library/jest-dom'
import { expect, afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

// Cleanup after each test case
afterEach(() => {
  cleanup()
})

// Mock window.electron for Electron/Tauri APIs
global.window = Object.create(window)
Object.defineProperty(window, 'electron', {
  value: {
    selectFolder: vi.fn(),
    selectFile: vi.fn(),
    showNotification: vi.fn(),
  },
  writable: true,
})

// Mock Tauri API
vi.mock('@tauri-apps/api/dialog', () => ({
  open: vi.fn(),
  save: vi.fn(),
  message: vi.fn(),
}))

vi.mock('@tauri-apps/api/fs', () => ({
  readTextFile: vi.fn(),
  writeTextFile: vi.fn(),
  readDir: vi.fn(),
}))
