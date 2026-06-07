/**
 * 项目管理E2E测试
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
 * 测试套件：项目管理
 */
test.describe('项目管理测试', () => {

  /**
   * 每个测试前登录
   */
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  /**
   * 测试用例：创建新项目
   * 验证能够成功创建新项目
   */
  test('创建新项目', async ({ page }) => {
    // 点击创建项目按钮
    const createButton = page.locator('.create-project-btn, [data-testid="create-project"], button:has-text("新建项目"), button:has-text("创建")').first();
    await createButton.click();

    // 等待对话框出现
    await page.waitForSelector('.el-dialog, .modal, .dialog', { state: 'visible' });

    // 填写项目信息
    const projectName = `测试项目-${Date.now()}`;
    await page.fill('input[name="name"], input[placeholder*="项目"], .el-dialog input', projectName);
    await page.fill('textarea[name="description"], textarea[placeholder*="描述"], .el-dialog textarea', '这是一个测试项目描述');

    // 点击确认按钮
    await page.click('.el-dialog__footer button:has-text("确定"), .el-dialog__footer button:has-text("创建"), .modal-footer button:has-text("确定")');

    // 等待项目创建成功提示
    await page.waitForTimeout(500);

    // 验证项目列表中显示新项目
    await expect(page.locator('text=' + projectName)).toBeVisible();
  });

  /**
   * 测试用例：查看项目列表
   * 验证项目列表正常显示
   */
  test('查看项目列表', async ({ page }) => {
    // 验证页面标题
    await expect(page.locator('h1, h2, .page-title')).toContainText(/项目|Project/);

    // 验证项目列表容器存在
    const projectList = page.locator('.project-list, .project-grid, [data-testid="project-list"]');
    await expect(projectList).toBeVisible();

    // 验证列表中有项目卡片或空状态提示
    const projectCards = page.locator('.project-card, .project-item');
    const emptyState = page.locator('.empty-state, .el-empty');
    
    const hasProjects = await projectCards.count() > 0;
    const hasEmptyState = await emptyState.isVisible().catch(() => false);
    
    expect(hasProjects || hasEmptyState).toBeTruthy();

    // 验证项目卡片显示必要信息（如果有项目）
    if (hasProjects) {
      const firstCard = projectCards.first();
      await expect(firstCard.locator('.project-name, .title, h3')).toBeVisible();
    }
  });

  /**
   * 测试用例：进入项目详情
   * 验证能够点击进入项目详情页面
   */
  test('进入项目详情', async ({ page }) => {
    // 查找第一个项目卡片
    const projectCard = page.locator('.project-card, .project-item').first();
    
    // 如果没有项目，先创建一个
    if (await projectCard.count() === 0) {
      // 创建项目
      await page.click('.create-project-btn, [data-testid="create-project"], button:has-text("新建")');
      await page.waitForSelector('.el-dialog, .modal', { state: 'visible' });
      await page.fill('.el-dialog input, .modal input', `测试项目-${Date.now()}`);
      await page.click('.el-dialog__footer button:has-text("确定"), .modal-footer button:has-text("确定")');
      await page.waitForTimeout(500);
    }

    // 点击第一个项目
    await page.locator('.project-card, .project-item').first().click();

    // 等待跳转到项目详情页
    await page.waitForURL(/.*projects\/.+/, { timeout: 3000 });

    // 验证项目详情页显示
    await expect(page).toHaveURL(/.*projects\/.+/);
    
    // 验证详情页包含项目信息
    await expect(page.locator('.project-detail, .project-info, h1, h2')).toBeVisible();
  });

  /**
   * 测试用例：编辑项目信息
   * 验证能够编辑项目信息
   */
  test('编辑项目信息', async ({ page }) => {
    // 先进入项目详情页
    const projectCard = page.locator('.project-card, .project-item').first();
    
    if (await projectCard.count() === 0) {
      // 创建项目
      await page.click('.create-project-btn, button:has-text("新建")');
      await page.waitForSelector('.el-dialog, .modal', { state: 'visible' });
      await page.fill('.el-dialog input, .modal input', `测试项目-${Date.now()}`);
      await page.click('.el-dialog__footer button:has-text("确定")');
      await page.waitForTimeout(500);
    }

    await page.locator('.project-card, .project-item').first().click();
    await page.waitForURL(/.*projects\/.+/, { timeout: 3000 });

    // 点击编辑按钮
    const editButton = page.locator('.edit-btn, [data-testid="edit-project"], button:has-text("编辑")').first();
    await editButton.click();

    // 等待编辑对话框
    await page.waitForSelector('.el-dialog, .modal, .edit-form', { state: 'visible' });

    // 修改项目名称
    const newName = `编辑后的项目-${Date.now()}`;
    const nameInput = page.locator('.el-dialog input, .modal input[name="name"], .edit-form input').first();
    await nameInput.fill('');
    await nameInput.fill(newName);

    // 保存修改
    await page.click('.el-dialog__footer button:has-text("确定"), .el-dialog__footer button:has-text("保存"), .modal-footer button:has-text("保存")');

    // 等待保存完成
    await page.waitForTimeout(500);

    // 验证项目名称已更新
    await expect(page.locator('text=' + newName)).toBeVisible();
  });

  /**
   * 测试用例：删除项目
   * 验证能够删除项目
   */
  test('删除项目', async ({ page }) => {
    // 先创建一个测试项目
    await page.click('.create-project-btn, button:has-text("新建")');
    await page.waitForSelector('.el-dialog, .modal', { state: 'visible' });
    const projectName = `待删除项目-${Date.now()}`;
    await page.fill('.el-dialog input, .modal input', projectName);
    await page.click('.el-dialog__footer button:has-text("确定")');
    await page.waitForTimeout(500);

    // 找到刚创建的项目卡片
    const projectCard = page.locator('.project-card, .project-item').filter({ hasText: projectName });
    
    // 悬停显示操作按钮
    await projectCard.hover();

    // 点击删除按钮
    const deleteButton = projectCard.locator('.delete-btn, [data-testid="delete-project"], button:has-text("删除")');
    await deleteButton.click();

    // 确认删除
    await page.waitForSelector('.el-message-box, .confirm-dialog, .modal', { state: 'visible' });
    await page.click('.el-message-box__btns button:has-text("确定"), .el-message-box__btns button:has-text("删除"), .confirm-dialog button:has-text("确定")');

    // 等待删除完成
    await page.waitForTimeout(500);

    // 验证项目已删除
    await expect(page.locator('text=' + projectName)).not.toBeVisible();
  });

  /**
   * 测试用例：分享项目
   * 验证能够生成项目分享链接
   */
  test('分享项目', async ({ page }) => {
    // 先进入项目详情页
    const projectCard = page.locator('.project-card, .project-item').first();
    
    if (await projectCard.count() === 0) {
      // 创建项目
      await page.click('.create-project-btn, button:has-text("新建")');
      await page.waitForSelector('.el-dialog, .modal', { state: 'visible' });
      await page.fill('.el-dialog input, .modal input', `测试项目-${Date.now()}`);
      await page.click('.el-dialog__footer button:has-text("确定")');
      await page.waitForTimeout(500);
    }

    await page.locator('.project-card, .project-item').first().click();
    await page.waitForURL(/.*projects\/.+/, { timeout: 3000 });

    // 点击分享按钮
    const shareButton = page.locator('.share-btn, [data-testid="share-project"], button:has-text("分享")').first();
    await shareButton.click();

    // 等待分享对话框
    await page.waitForSelector('.el-dialog, .share-dialog, .modal', { state: 'visible' });

    // 验证分享选项存在
    await expect(page.locator('.share-options, .share-link, input[value*="http"]')).toBeVisible();

    // 生成分享链接
    const generateButton = page.locator('button:has-text("生成链接"), button:has-text("创建分享")').first();
    if (await generateButton.isVisible().catch(() => false)) {
      await generateButton.click();
      await page.waitForTimeout(500);
    }

    // 验证分享链接已生成
    const shareLink = page.locator('.share-link input, input[readonly], .link-text');
    const linkValue = await shareLink.inputValue().catch(() => '');
    expect(linkValue).toMatch(/http|share/);

    // 关闭分享对话框
    await page.click('.el-dialog__headerbtn, .modal-close, button:has-text("关闭")');
  });

  /**
   * 测试用例：项目搜索
   * 验证能够搜索项目
   */
  test('项目搜索', async ({ page }) => {
    // 查找搜索框
    const searchInput = page.locator('input[type="search"], input[placeholder*="搜索"], .search-input input');
    
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
   * 测试用例：项目排序
   * 验证能够按不同方式排序项目
   */
  test('项目排序', async ({ page }) => {
    // 查找排序选择器
    const sortSelect = page.locator('.sort-select, .el-select, select');
    
    if (await sortSelect.isVisible().catch(() => false)) {
      // 点击排序选择器
      await sortSelect.click();
      
      // 选择按名称排序
      await page.click('text=名称');
      await page.waitForTimeout(300);

      // 选择按时间排序
      await sortSelect.click();
      await page.click('text=时间');
      await page.waitForTimeout(300);
    }
  });

});
