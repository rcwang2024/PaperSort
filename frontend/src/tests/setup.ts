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

// Mock window.electron (the API exposed by electron/preload.js)
global.window = Object.create(window)
Object.defineProperty(window, 'electron', {
  value: {
    selectFolder: vi.fn(),
    selectFile: vi.fn(),
    showNotification: vi.fn(),
  },
  writable: true,
})
