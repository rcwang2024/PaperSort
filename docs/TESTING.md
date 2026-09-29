# Testing Guide for PaperSort

This document describes the comprehensive testing setup for PaperSort v2.0.

## Overview

The project uses a **spec coding** approach with automated tests to prevent regressions and ensure reliability. Tests are organized into three categories:

1. **Backend Unit Tests** - Test individual components and services
2. **Backend Integration Tests** - Test API endpoints and workflows
3. **Frontend Unit Tests** - Test React components and services
4. **E2E Tests** - Test complete user flows end-to-end

## Backend Testing (Python/pytest)

### Setup

Backend tests use **pytest** with async support. Tests are located in `backend/tests/`.

**Test Structure:**
```
backend/tests/
├── conftest.py          # Shared fixtures
├── unit/                # Unit tests
│   └── test_database.py
└── integration/         # Integration tests
    ├── test_organize_api.py
    ├── test_mindmap_api.py
    └── test_papers_api.py
```

### Running Backend Tests

```bash
# Run all backend tests
npm run test:backend

# Run only unit tests
npm run test:backend:unit

# Run only integration tests
npm run test:backend:integration

# Run with coverage report
npm run test:backend:coverage
```

Or directly with pytest:
```bash
cd backend
source venv/bin/activate
pytest                          # All tests
pytest tests/unit              # Unit tests only
pytest tests/integration       # Integration tests only
pytest -v                      # Verbose output
pytest --cov=app              # With coverage
```

### Backend Test Coverage

**Critical paths tested:**
- ✅ Paper organization API (`/api/organize`)
- ✅ Async organization with status tracking
- ✅ Mind-map generation API (`/api/mindmap/generate`)
- ✅ Paper upload and management
- ✅ Database operations (CRUD)
- ✅ Input validation
- ✅ Error handling

## Frontend Testing (Vitest + Playwright)

### Setup

Frontend uses **Vitest** for unit tests and **Playwright** for E2E tests.

**Test Structure:**
```
frontend/
├── src/tests/           # Unit tests
│   ├── setup.ts
│   ├── FolderSelector.test.tsx
│   └── api.test.ts
└── e2e/                 # E2E tests
    ├── organize-papers.spec.ts
    └── mindmap.spec.ts
```

### Running Frontend Tests

```bash
# Run frontend unit tests
npm run test:frontend

# Run with UI (interactive mode)
npm run test:frontend:ui

# Run with coverage
npm run test:frontend:coverage

# Run E2E tests
npm run test:e2e
```

Or directly:
```bash
cd frontend
npm test                # Unit tests
npm run test:ui        # Interactive UI
npm run test:e2e       # E2E tests with Playwright
```

### Frontend Test Coverage

**Components tested:**
- ✅ FolderSelector component
- ✅ API service methods
- ✅ Form validation
- ✅ User interactions
- ✅ Error handling

**E2E flows tested:**
- ✅ Paper organization workflow
- ✅ Folder selection
- ✅ Options configuration
- ✅ Mind-map generation (UI)

## Running All Tests

```bash
# Run backend + frontend unit tests
npm test

# Run everything including E2E
npm run test:all
```

## Test Configuration Files

### Backend (`backend/pytest.ini`)
```ini
[pytest]
testpaths = tests
asyncio_mode = auto
addopts = -v --cov=app --cov-report=html
```

### Frontend (`frontend/vite.config.ts`)
```typescript
test: {
  globals: true,
  environment: 'jsdom',
  setupFiles: './src/tests/setup.ts',
}
```

### E2E (`frontend/playwright.config.ts`)
- Tests run in Chromium
- Screenshots on failure
- Automatic dev server startup

## Writing New Tests

### Backend Test Example

```python
# tests/integration/test_my_api.py
import pytest
from httpx import AsyncClient

@pytest.mark.integration
async def test_my_endpoint(client: AsyncClient):
    response = await client.post("/api/my-endpoint", json={...})
    assert response.status_code == 200
    assert response.json()["success"] is True
```

### Frontend Unit Test Example

```typescript
// src/tests/MyComponent.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import MyComponent from '../components/MyComponent'

describe('MyComponent', () => {
  it('renders correctly', () => {
    render(<MyComponent />)
    expect(screen.getByText('Hello')).toBeInTheDocument()
  })
})
```

### E2E Test Example

```typescript
// e2e/my-flow.spec.ts
import { test, expect } from '@playwright/test'

test('user can complete workflow', async ({ page }) => {
  await page.goto('/')
  await page.getByText('Button').click()
  await expect(page.getByText('Success')).toBeVisible()
})
```

## Best Practices

1. **Run tests before committing** - Catch issues early
2. **Write tests for new features** - Before or immediately after implementation
3. **Test critical paths thoroughly** - Organization, mindmap generation, data handling
4. **Mock external dependencies** - LLMs, file system operations
5. **Keep tests fast** - Use in-memory databases, mock slow operations
6. **Test error cases** - Not just happy paths

## CI/CD Integration

Tests are designed to run in CI/CD pipelines:

```bash
# Install dependencies
npm install
cd backend && pip install -r requirements.txt

# Run tests
npm run test:all
```

## Troubleshooting

### Backend tests failing with "module not found"
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### Frontend tests failing with "Cannot find module"
```bash
cd frontend
npm install
```

### E2E tests failing to start
- Ensure dev server starts: `npm run dev`
- Check port 1420 is available
- Backend should be running on port 8000

### Database errors in tests
- Tests use in-memory SQLite (`:memory:`)
- No cleanup needed between runs

## Coverage Reports

After running tests with coverage:

**Backend:** Open `backend/htmlcov/index.html`
**Frontend:** Open `frontend/coverage/index.html`

## Benefits of This Testing Setup

✅ **Catch regressions before they reach production**
✅ **Safe refactoring** - Tests verify nothing breaks
✅ **Documentation** - Tests show how features should work
✅ **Faster debugging** - Tests identify exactly what broke
✅ **Confidence when adding features** - Run tests to ensure existing functionality still works

---

**Questions?** Check test files in `backend/tests/` and `frontend/src/tests/` for examples.
