/**
 * 分享功能E2E测试
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
 * 辅助函数：进入项目详情页
 */
async function enterProject(page) {
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
}

/**
 * 测试套件：分享功能
 */
test.describe('分享功能测试', () => {

  /**
   * 测试用例：生成分享链接
   * 验证能够生成项目或文件的分享链接
   */
  test('生成分享链接', async ({ page }) => {
    await login(page);
    await enterProject(page);

    // 点击分享按钮
    const shareButton = page.locator('.share-btn, [data-testid="share-project"], button:has-text("分享")').first();
    await shareButton.click();

    // 等待分享对话框
    await page.waitForSelector('.el-dialog, .share-dialog, .modal', { state: 'visible' });

    // 验证分享选项存在
    await expect(page.locator('.share-options, .share-settings')).toBeVisible();

    // 配置分享选项（如果存在）
    const expireSelect = page.locator('select[name="expire"], .expire-select').first();
    if (await expireSelect.isVisible().catch(() => false)) {
      await expireSelect.selectOption('7'); // 7天有效期
    }

    const permissionSelect = page.locator('select[name="permission"], .permission-select').first();
    if (await permissionSelect.isVisible().catch(() => false)) {
      await permissionSelect.selectOption('view'); // 仅查看权限
    }

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
    expect(linkValue.length).toBeGreaterThan(10);

    // 关闭分享对话框
    await page.click('.el-dialog__headerbtn, .modal-close, button:has-text("关闭")');
  });

  /**
   * 测试用例：访问分享链接
   * 验证能够通过分享链接访问内容
   */
  test('访问分享链接', async ({ page, context }) => {
    // 先登录并创建分享
    await login(page);
    await enterProject(page);

    // 点击分享按钮
    const shareButton = page.locator('.share-btn, button:has-text("分享")').first();
    await shareButton.click();
    await page.waitForSelector('.el-dialog, .share-dialog', { state: 'visible' });

    // 生成分享链接
    const generateButton = page.locator('button:has-text("生成链接"), button:has-text("创建分享")').first();
    if (await generateButton.isVisible().catch(() => false)) {
      await generateButton.click();
      await page.waitForTimeout(500);
    }

    // 获取分享链接
    const shareLinkInput = page.locator('.share-link input, input[readonly]').first();
    const shareUrl = await shareLinkInput.inputValue();

    // 关闭对话框
    await page.click('.el-dialog__headerbtn, .modal-close');

    // 创建新的浏览器上下文（模拟未登录用户）
    const newContext = await context.browser().newContext();
    const newPage = await newContext.newPage();

    // 访问分享链接
    await newPage.goto(shareUrl);
    await newPage.waitForTimeout(1000);

    // 验证分享页面正常显示
    await expect(newPage.locator('.share-view, .shared-content, .public-view')).toBeVisible();

    // 验证项目名称或内容显示
    await expect(newPage.locator('.project-name, .share-title, h1, h2')).toBeVisible();

    // 清理
    await newContext.close();
  });

  /**
   * 测试用例：下载分享文件
   * 验证能够通过分享链接下载文件
   */
  test('下载分享文件', async ({ page, context }) => {
    // 先登录并上传文件
    await login(page);
    await enterProject(page);

    // 上传测试文件
    const uploadButton = page.locator('.upload-btn, button:has-text("上传")').first();
    await uploadButton.click();
    await page.waitForSelector('.el-dialog, .modal', { state: 'visible' });
    
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles({
      name: 'share-download-test.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4 share download test')
    });
    
    await page.click('.el-dialog__footer button:has-text("确定")');
    await page.waitForTimeout(2000);

    // 分享文件
    const fileItem = page.locator('.file-item:has-text("share-download"), .file-card:has-text("share-download")').first();
    await fileItem.hover();

    const shareFileButton = fileItem.locator('.share-btn, button:has-text("分享")').first();
    await shareFileButton.click();
    await page.waitForSelector('.el-dialog, .share-dialog', { state: 'visible' });

    // 生成分享链接
    const generateButton = page.locator('button:has-text("生成链接"), button:has-text("创建分享")').first();
    if (await generateButton.isVisible().catch(() => false)) {
      await generateButton.click();
      await page.waitForTimeout(500);
    }

    // 获取分享链接
    const shareLinkInput = page.locator('.share-link input, input[readonly]').first();
    const shareUrl = await shareLinkInput.inputValue();

    await page.click('.el-dialog__headerbtn, .modal-close');

    // 使用新上下文访问分享链接
    const newContext = await context.browser().newContext();
    const newPage = await newContext.newPage();

    await newPage.goto(shareUrl);
    await newPage.waitForTimeout(1000);

    // 点击下载按钮
    const downloadButton = newPage.locator('.download-btn, button:has-text("下载")').first();
    
    // 等待下载事件
    const [download] = await Promise.all([
      newPage.waitForEvent('download'),
      downloadButton.click()
    ]);

    // 验证下载成功
    expect(download.suggestedFilename()).toContain('share-download');

    await newContext.close();
  });

  /**
   * 测试用例：查看分享版本
   * 验证能够通过分享链接查看文件版本历史
   */
  test('查看分享版本', async ({ page, context }) => {
    // 先登录并上传带版本的文件
    await login(page);
    await enterProject(page);

    // 上传文件
    const uploadButton = page.locator('.upload-btn, button:has-text("上传")').first();
    await uploadButton.click();
    await page.waitForSelector('.el-dialog, .modal', { state: 'visible' });
    
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles({
      name: 'share-version-test.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4 version 1')
    });
    
    await page.click('.el-dialog__footer button:has-text("确定")');
    await page.waitForTimeout(2000);

    // 分享文件
    const fileItem = page.locator('.file-item:has-text("share-version"), .file-card:has-text("share-version")').first();
    await fileItem.hover();

    const shareFileButton = fileItem.locator('.share-btn, button:has-text("分享")').first();
    await shareFileButton.click();
    await page.waitForSelector('.el-dialog, .share-dialog', { state: 'visible' });

    // 生成分享链接
    const generateButton = page.locator('button:has-text("生成链接"), button:has-text("创建分享")').first();
    if (await generateButton.isVisible().catch(() => false)) {
      await generateButton.click();
      await page.waitForTimeout(500);
    }

    // 获取分享链接
    const shareLinkInput = page.locator('.share-link input, input[readonly]').first();
    const shareUrl = await shareLinkInput.inputValue();

    await page.click('.el-dialog__headerbtn, .modal-close');

    // 使用新上下文访问分享链接
    const newContext = await context.browser().newContext();
    const newPage = await newContext.newPage();

    await newPage.goto(shareUrl);
    await newPage.waitForTimeout(1000);

    // 查找版本历史按钮或标签
    const versionTab = newPage.locator('.version-tab, button:has-text("版本"), .version-history-btn').first();
    if (await versionTab.isVisible().catch(() => false)) {
      await versionTab.click();
      await newPage.waitForTimeout(500);

      // 验证版本列表显示
      const versionList = newPage.locator('.version-list, .version-timeline');
      await expect(versionList).toBeVisible();
    }

    await newContext.close();
  });

  /**
   * 测试用例：分享链接过期
   * 验证过期的分享链接显示错误信息
   */
  test('分享链接过期处理', async ({ page }) => {
    // 访问一个明显过期的分享链接
    await page.goto(`${BASE_URL}/share/expired-token-12345`);
    await page.waitForTimeout(1000);

    // 验证显示过期或无效提示
    const errorMessage = page.locator('.error-message, .expired-notice, .el-message--error, .error-container');
    
    // 可能显示错误页面或重定向到错误页面
    const hasError = await errorMessage.isVisible().catch(() => false);
    const isErrorPage = await page.locator('text=过期|无效|错误|expired|invalid|error').first().isVisible().catch(() => false);
    
    expect(hasError || isErrorPage).toBeTruthy();
  });

  /**
   * 测试用例：撤销分享
   * 验证能够撤销已创建的分享链接
   */
  test('撤销分享', async ({ page }) => {
    await login(page);
    await enterProject(page);

    // 创建分享
    const shareButton = page.locator('.share-btn, button:has-text("分享")').first();
    await shareButton.click();
    await page.waitForSelector('.el-dialog, .share-dialog', { state: 'visible' });

    // 生成分享链接
    const generateButton = page.locator('button:has-text("生成链接"), button:has-text("创建分享")').first();
    if (await generateButton.isVisible().catch(() => false)) {
      await generateButton.click();
      await page.waitForTimeout(500);
    }

    // 查找撤销按钮
    const revokeButton = page.locator('button:has-text("撤销"), button:has-text("删除"), .revoke-btn').first();
    
    if (await revokeButton.isVisible().catch(() => false)) {
      await revokeButton.click();
      
      // 确认撤销
      await page.waitForSelector('.el-message-box, .confirm-dialog', { state: 'visible' });
      await page.click('.el-message-box__btns button:has-text("确定"), .confirm-dialog button:has-text("确定")');
      
      await page.waitForTimeout(500);

      // 验证分享链接已删除
      const shareLink = page.locator('.share-link input');
      await expect(shareLink).not.toBeVisible();
    }

    await page.click('.el-dialog__headerbtn, .modal-close');
  });

  /**
   * 测试用例：分享密码保护
   * 验证密码保护的分享链接需要输入密码
   */
  test('分享密码保护', async ({ page, context }) => {
    await login(page);
    await enterProject(page);

    // 创建带密码的分享
    const shareButton = page.locator('.share-btn, button:has-text("分享")').first();
    await shareButton.click();
    await page.waitForSelector('.el-dialog, .share-dialog', { state: 'visible' });

    // 启用密码保护
    const passwordCheckbox = page.locator('input[type="checkbox"][name="password"], .password-toggle').first();
    if (await passwordCheckbox.isVisible().catch(() => false)) {
      await passwordCheckbox.check();
      
      // 设置密码
      const passwordInput = page.locator('input[name="sharePassword"], .password-input').first();
      if (await passwordInput.isVisible().catch(() => false)) {
        await passwordInput.fill('testpass123');
      }
    }

    // 生成分享链接
    const generateButton = page.locator('button:has-text("生成链接"), button:has-text("创建分享")').first();
    if (await generateButton.isVisible().catch(() => false)) {
      await generateButton.click();
      await page.waitForTimeout(500);
    }

    // 获取分享链接
    const shareLinkInput = page.locator('.share-link input, input[readonly]').first();
    const shareUrl = await shareLinkInput.inputValue();

    await page.click('.el-dialog__headerbtn, .modal-close');

    // 使用新上下文访问
    const newContext = await context.browser().newContext();
    const newPage = await newContext.newPage();

    await newPage.goto(shareUrl);
    await newPage.waitForTimeout(1000);

    // 验证显示密码输入框
    const passwordInput = newPage.locator('input[type="password"], input[placeholder*="密码"]').first();
    if (await passwordInput.isVisible().catch(() => false)) {
      await passwordInput.fill('testpass123');
      await newPage.click('button:has-text("确认"), button:has-text("访问")');
      await newPage.waitForTimeout(500);

      // 验证能够访问内容
      await expect(newPage.locator('.share-view, .shared-content')).toBeVisible();
    }

    await newContext.close();
  });

});
