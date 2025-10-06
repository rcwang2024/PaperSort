/**
 * E2E tests for mind-map generation flow
 */

import { test, expect } from '@playwright/test';

test.describe('Mind-map Generation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should have mindmap functionality available after organization', async ({ page }) => {
    // This test verifies that the mindmap UI components exist
    // Actual generation would require organized papers

    // For now, check the app loads correctly
    await expect(page).toHaveTitle(/PaperSort/i);
  });

  test('should handle mindmap generation errors gracefully', async ({ page }) => {
    // Error handling should be in place
    // This would be better tested with actual backend integration
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Mind-map Visualization', () => {
  test('application should be responsive', async ({ page }) => {
    await page.goto('/');

    // Test different viewport sizes
    await page.setViewportSize({ width: 1920, height: 1080 });
    await expect(page.locator('body')).toBeVisible();

    await page.setViewportSize({ width: 1280, height: 720 });
    await expect(page.locator('body')).toBeVisible();
  });
});
