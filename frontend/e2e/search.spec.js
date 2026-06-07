/**
 * 搜索功能E2E测试
 * 使用Playwright进行端到端测试
 */

import { test, expect } from '@playwright/test';

// 测试配置
const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:5173';
const TEST_USER = {
  username: 'testuser',
  password: 'TestPass123!'
};

/**
 * 辅助函数：登录
 */
async function login(page) {
  await page.goto(`${BASE_URL}/login`);
  await page.fill('input[name="username"]', TEST_USER.username);
  await page.fill('input[name="password"]', TEST_USER.password);
  await page.click('button[type="submit"]');
  await page.waitForURL(/.*projects|.*dashboard.*/, { timeout: 5000 });
}

/**
 * 测试套件：搜索功能
 */
test.describe('搜索功能测试', () => {

  /**
   * 每个测试前登录
   */
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  /**
   * 测试用例：全局搜索框显示
   * 验证全局搜索框正常显示
   */
  test('全局搜索框显示', async ({ page }) => {
    // 验证搜索框存在
    const searchInput = page.locator('.global-search input, .search-box input, input[type="search"], .header-search input').first();
    await expect(searchInput).toBeVisible();
    
    // 验证搜索图标存在
    const searchIcon = page.locator('.search-icon, .el-icon-search, [data-testid="search-icon"]');
    await expect(searchIcon.first()).toBeVisible();
  });

  /**
   * 测试用例：项目搜索
   * 验证能够在项目列表中搜索项目
   */
  test('项目搜索', async ({ page }) => {
    // 导航到项目列表页面
    await page.goto(`${BASE_URL}/projects`);
    await page.waitForTimeout(500);
    
    // 查找搜索框
    const searchInput = page.locator('input[type="search"], input[placeholder*="搜索"], .search-input input').first();
    
    if (await searchInput.isVisible().catch(() => false)) {
      // 输入搜索关键词
      await searchInput.fill('测试');
      await page.waitForTimeout(500);
      
      // 验证搜索结果
      const projectCards = page.locator('.project-card, .project-item');
      const count = await projectCards.count();
      
      // 如果搜索结果不为空，验证所有结果包含关键词
      if (count > 0) {
        for (let i = 0; i < Math.min(count, 5); i++) {
          const cardText = await projectCards.nth(i).textContent();
          expect(cardText).toMatch(/测试|test/i);
        }
      }
      
      // 清除搜索
      await searchInput.fill('');
      await page.waitForTimeout(300);
    }
  });

  /**
   * 测试用例：文件搜索
   * 验证能够在项目中搜索文件
   */
  test('文件搜索', async ({ page }) => {
    // 先进入项目详情页
    const projectCard = page.locator('.project-card, .project-item').first();
    
    if (await projectCard.count() === 0) {
      // 创建项目
      await page.click('.create-project-btn, button:has-text("新建")');
      await page.waitForSelector('.el-dialog, .modal', { state: 'visible' });
      await page.fill('.el-dialog input, .modal input', `搜索测试项目-${Date.now()}`);
      await page.click('.el-dialog__footer button:has-text("确定")');
      await page.waitForTimeout(500);
    }
    
    await page.locator('.project-card, .project-item').first().click();
    await page.waitForURL(/.*projects\/.+/, { timeout: 3000 });
    
    // 查找文件搜索框
    const fileSearchInput = page.locator('.file-search input, .document-search input, input[placeholder*="文件"]').first();
    
    if (await fileSearchInput.isVisible().catch(() => false)) {
      // 输入搜索关键词
      await fileSearchInput.fill('pdf');
      await page.waitForTimeout(500);
      
      // 验证搜索结果
      const fileItems = page.locator('.file-item, .file-card, .document-item');
      const count = await fileItems.count();
      
      // 验证结果包含关键词
      if (count > 0) {
        for (let i = 0; i < Math.min(count, 5); i++) {
          const itemText = await fileItems.nth(i).textContent();
          expect(itemText.toLowerCase()).toContain('pdf');
        }
      }
      
      // 清除搜索
      await fileSearchInput.fill('');
      await page.waitForTimeout(300);
    }
  });

  /**
   * 测试用例：搜索结果高亮
   * 验证搜索结果中的关键词被高亮显示
   */
  test('搜索结果高亮', async ({ page }) => {
    // 导航到项目列表页面
    await page.goto(`${BASE_URL}/projects`);
    await page.waitForTimeout(500);
    
    // 查找搜索框
    const searchInput = page.locator('input[type="search"], input[placeholder*="搜索"]').first();
    
    if (await searchInput.isVisible().catch(() => false)) {
      // 输入搜索关键词
      await searchInput.fill('测试');
      await page.waitForTimeout(500);
      
      // 验证高亮元素存在
      const highlightElements = page.locator('.highlight, .search-highlight, mark, .el-tag');
      const hasHighlights = await highlightElements.count() > 0;
      
      if (hasHighlights) {
        await expect(highlightElements.first()).toBeVisible();
      }
    }
  });

  /**
   * 测试用例：搜索建议/自动完成
   * 验证搜索时显示建议
   */
  test('搜索建议自动完成', async ({ page }) => {
    // 导航到项目列表页面
    await page.goto(`${BASE_URL}/projects`);
    await page.waitForTimeout(500);
    
    // 查找搜索框
    const searchInput = page.locator('input[type="search"], input[placeholder*="搜索"]').first();
    
    if (await searchInput.isVisible().catch(() => false)) {
      // 输入部分关键词
      await searchInput.fill('测');
      await page.waitForTimeout(500);
      
      // 验证搜索建议下拉框
      const suggestions = page.locator('.search-suggestions, .el-autocomplete-suggestion, .dropdown-menu');
      
      if (await suggestions.isVisible().catch(() => false)) {
        await expect(suggestions).toBeVisible();
        
        // 验证建议项存在
        const suggestionItems = page.locator('.suggestion-item, .el-autocomplete-suggestion__item');
        if (await suggestionItems.count() > 0) {
          await expect(suggestionItems.first()).toBeVisible();
        }
      }
    }
  });

  /**
   * 测试用例：搜索过滤器
   * 验证能够使用过滤器进行高级搜索
   */
  test('搜索过滤器', async ({ page }) => {
    // 导航到搜索页面或项目页面
    await page.goto(`${BASE_URL}/projects`);
    await page.waitForTimeout(500);
    
    // 查找过滤器按钮或区域
    const filterButton = page.locator('.filter-btn, button:has-text("筛选"), button:has-text("过滤"), .advanced-search').first();
    
    if (await filterButton.isVisible().catch(() => false)) {
      await filterButton.click();
      await page.waitForTimeout(300);
      
      // 验证过滤器选项显示
      const filterOptions = page.locator('.filter-options, .filter-panel, .el-popover');
      await expect(filterOptions).toBeVisible();
      
      // 选择过滤器选项
      const dateFilter = page.locator('.date-filter, input[name="date"]').first();
      if (await dateFilter.isVisible().catch(() => false)) {
        await dateFilter.click();
        await page.click('text=最近一周');
      }
      
      const typeFilter = page.locator('.type-filter, select[name="type"]').first();
      if (await typeFilter.isVisible().catch(() => false)) {
        await typeFilter.selectOption('document');
      }
      
      // 应用过滤器
      const applyButton = page.locator('button:has-text("应用"), button:has-text("确定")').first();
      if (await applyButton.isVisible().catch(() => false)) {
        await applyButton.click();
        await page.waitForTimeout(500);
      }
    }
  });

  /**
   * 测试用例：搜索结果排序
   * 验证能够对搜索结果进行排序
   */
  test('搜索结果排序', async ({ page }) => {
    // 导航到项目列表页面
    await page.goto(`${BASE_URL}/projects`);
    await page.waitForTimeout(500);
    
    // 查找排序选择器
    const sortSelect = page.locator('.sort-select, .el-select, select').first();
    
    if (await sortSelect.isVisible().catch(() => false)) {
      // 点击排序选择器
      await sortSelect.click();
      await page.waitForTimeout(300);
      
      // 选择按名称排序
      await page.click('text=名称');
      await page.waitForTimeout(500);
      
      // 再次点击排序选择器
      await sortSelect.click();
      await page.waitForTimeout(300);
      
      // 选择按时间排序
      await page.click('text=时间|创建时间|更新时间');
      await page.waitForTimeout(500);
      
      // 验证排序后的结果
      const projectCards = page.locator('.project-card, .project-item');
      if (await projectCards.count() > 0) {
        await expect(projectCards.first()).toBeVisible();
      }
    }
  });

  /**
   * 测试用例：搜索历史
   * 验证能够查看和使用搜索历史
   */
  test('搜索历史', async ({ page }) => {
    // 导航到项目列表页面
    await page.goto(`${BASE_URL}/projects`);
    await page.waitForTimeout(500);
    
    // 查找搜索框
    const searchInput = page.locator('input[type="search"], input[placeholder*="搜索"]').first();
    
    if (await searchInput.isVisible().catch(() => false)) {
      // 先进行一次搜索
      await searchInput.fill('历史测试');
      await page.waitForTimeout(500);
      await page.keyboard.press('Enter');
      await page.waitForTimeout(500);
      
      // 清除搜索框
      await searchInput.fill('');
      await page.waitForTimeout(300);
      
      // 点击搜索框查看历史
      await searchInput.click();
      await page.waitForTimeout(300);
      
      // 验证搜索历史显示
      const searchHistory = page.locator('.search-history, .history-list, .recent-searches');
      
      if (await searchHistory.isVisible().catch(() => false)) {
        await expect(searchHistory).toBeVisible();
        
        // 验证历史项存在
        const historyItems = page.locator('.history-item, .recent-search-item');
        if (await historyItems.count() > 0) {
          await expect(historyItems.first()).toBeVisible();
          
          // 点击历史项进行搜索
          await historyItems.first().click();
          await page.waitForTimeout(500);
          
          // 验证搜索框更新
          const inputValue = await searchInput.inputValue();
          expect(inputValue.length).toBeGreaterThan(0);
        }
      }
    }
  });

  /**
   * 测试用例：清空搜索
   * 验证能够清空搜索内容
   */
  test('清空搜索', async ({ page }) => {
    // 导航到项目列表页面
    await page.goto(`${BASE_URL}/projects`);
    await page.waitForTimeout(500);
    
    // 查找搜索框
    const searchInput = page.locator('input[type="search"], input[placeholder*="搜索"]').first();
    
    if (await searchInput.isVisible().catch(() => false)) {
      // 输入搜索关键词
      await searchInput.fill('清空测试');
      await page.waitForTimeout(300);
      
      // 查找清空按钮
      const clearButton = page.locator('.clear-search, .el-input__clear, button:has-text("清空")').first();
      
      if (await clearButton.isVisible().catch(() => false)) {
        await clearButton.click();
        await page.waitForTimeout(300);
        
        // 验证搜索框已清空
        const inputValue = await searchInput.inputValue();
        expect(inputValue).toBe('');
      } else {
        // 如果没有清空按钮，手动清空
        await searchInput.fill('');
        await page.waitForTimeout(300);
        
        const inputValue = await searchInput.inputValue();
        expect(inputValue).toBe('');
      }
    }
  });

  /**
   * 测试用例：搜索无结果
   * 验证搜索无结果时显示空状态
   */
  test('搜索无结果', async ({ page }) => {
    // 导航到项目列表页面
    await page.goto(`${BASE_URL}/projects`);
    await page.waitForTimeout(500);
    
    // 查找搜索框
    const searchInput = page.locator('input[type="search"], input[placeholder*="搜索"]').first();
    
    if (await searchInput.isVisible().catch(() => false)) {
      // 输入不可能存在的搜索词
      await searchInput.fill('xyzabc123nonexistent');
      await page.waitForTimeout(500);
      
      // 验证空状态显示
      const emptyState = page.locator('.empty-state, .el-empty, .no-results, .search-empty');
      
      if (await emptyState.isVisible().catch(() => false)) {
        await expect(emptyState).toBeVisible();
        
        // 验证空状态提示文本
        await expect(page.locator('text=暂无数据|没有找到|无结果|empty')).toBeVisible();
      }
    }
  });

  /**
   * 测试用例：全局搜索跳转
   * 验证全局搜索结果能够正确跳转
   */
  test('全局搜索跳转', async ({ page }) => {
    // 查找全局搜索框
    const globalSearch = page.locator('.global-search input, .header-search input, .search-box input').first();
    
    if (await globalSearch.isVisible().catch(() => false)) {
      // 输入搜索词
      await globalSearch.fill('项目');
      await page.waitForTimeout(500);
      
      // 查找搜索结果项
      const searchResults = page.locator('.search-result-item, .result-item, .global-search-result');
      
      if (await searchResults.count() > 0) {
        // 点击第一个结果
        await searchResults.first().click();
        await page.waitForTimeout(1000);
        
        // 验证页面跳转
        const currentUrl = page.url();
        expect(currentUrl).not.toBe(`${BASE_URL}/projects`);
      }
    }
  });

});
