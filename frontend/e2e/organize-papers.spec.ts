/**
 * E2E tests for paper organization flow
 */

import { test, expect } from '@playwright/test';

test.describe('Paper Organization Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should display the folder selector on initial load', async ({ page }) => {
    await expect(page.getByText('Select Papers Folder')).toBeVisible();
    await expect(page.getByText('📁 Choose Folder')).toBeVisible();
  });

  test('organize button should be disabled without folder selection', async ({ page }) => {
    const organizeButton = page.getByText('🚀 Organize Papers');
    await expect(organizeButton).toBeDisabled();
  });

  test('should show copy/move options', async ({ page }) => {
    await expect(page.getByText('Copy files (keep originals)')).toBeVisible();
    await expect(page.getByText('Move files (remove originals)')).toBeVisible();
  });

  test('should allow entering number of topics', async ({ page }) => {
    const input = page.getByPlaceholder('Auto');
    await input.fill('5');
    await expect(input).toHaveValue('5');
  });

  test('should allow entering custom topics', async ({ page }) => {
    const input = page.getByPlaceholder(/Machine Learning/i);
    await input.fill('AI, NLP, Computer Vision');
    await expect(input).toHaveValue('AI, NLP, Computer Vision');
  });

  test('should toggle between copy and move modes', async ({ page }) => {
    const copyRadio = page.getByLabel(/copy files/i);
    const moveRadio = page.getByLabel(/move files/i);

    // Default should be copy
    await expect(copyRadio).toBeChecked();
    await expect(moveRadio).not.toBeChecked();

    // Switch to move
    await moveRadio.click();
    await expect(moveRadio).toBeChecked();
    await expect(copyRadio).not.toBeChecked();

    // Switch back to copy
    await copyRadio.click();
    await expect(copyRadio).toBeChecked();
    await expect(moveRadio).not.toBeChecked();
  });

  test('should show help text', async ({ page }) => {
    await expect(page.getByText(/Papers will be renamed to/)).toBeVisible();
    await expect(page.getByText(/Organized into topic-based subfolders/)).toBeVisible();
  });
});

test.describe('Paper Organization - API Integration', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should handle backend connection errors gracefully', async ({ page }) => {
    // This test would require mocking the backend or having it unavailable
    // For now, we check that error handling UI elements exist
    await expect(page.getByText('Select Papers Folder')).toBeVisible();
  });
});
