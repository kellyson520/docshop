/**
 * 文件管理E2E测试
 * 使用Playwright进行端到端测试
 */

import { test, expect } from '@playwright/test';
import path from 'path';

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
 * 测试套件：文件管理
 */
test.describe('文件管理测试', () => {

  /**
   * 每个测试前登录并进入项目
   */
  test.beforeEach(async ({ page }) => {
    await login(page);
    await enterProject(page);
  });

  /**
   * 测试用例：上传文件
   * 验证能够成功上传文件到项目
   */
  test('上传文件', async ({ page }) => {
    // 点击上传按钮
    const uploadButton = page.locator('.upload-btn, [data-testid="upload-file"], button:has-text("上传"), button:has-text("Upload")').first();
    await uploadButton.click();

    // 等待上传对话框
    await page.waitForSelector('.el-dialog, .upload-dialog, .modal', { state: 'visible' });

    // 选择文件
    const fileInput = page.locator('input[type="file"]').first();
    
    // 创建一个测试文件
    const testFilePath = path.join(process.cwd(), 'test-upload.pdf');
    await fileInput.setInputFiles({
      name: 'test-upload.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4 test content')
    });

    // 点击确认上传
    await page.click('.el-dialog__footer button:has-text("确定"), .el-dialog__footer button:has-text("上传"), .modal-footer button:has-text("上传")');

    // 等待上传完成
    await page.waitForTimeout(2000);

    // 验证文件出现在列表中
    await expect(page.locator('text=test-upload')).toBeVisible();
  });

  /**
   * 测试用例：查看文件列表
   * 验证文件列表正常显示
   */
  test('查看文件列表', async ({ page }) => {
    // 验证文件列表容器存在
    const fileList = page.locator('.file-list, .file-grid, [data-testid="file-list"], .document-list');
    await expect(fileList).toBeVisible();

    // 验证文件列表标题或表头
    const listHeader = page.locator('.file-list-header, .list-header, th');
    if (await listHeader.count() > 0) {
      await expect(listHeader.first()).toBeVisible();
    }

    // 验证列表中有文件或空状态提示
    const fileItems = page.locator('.file-item, .file-card, .document-item');
    const emptyState = page.locator('.empty-state, .el-empty, .no-files');
    
    const hasFiles = await fileItems.count() > 0;
    const hasEmptyState = await emptyState.isVisible().catch(() => false);
    
    expect(hasFiles || hasEmptyState).toBeTruthy();

    // 验证文件项显示必要信息（如果有文件）
    if (hasFiles) {
      const firstFile = fileItems.first();
      await expect(firstFile.locator('.file-name, .name, .filename')).toBeVisible();
    }
  });

  /**
   * 测试用例：下载文件
   * 验证能够下载文件
   */
  test('下载文件', async ({ page }) => {
    // 先上传一个测试文件
    const uploadButton = page.locator('.upload-btn, button:has-text("上传")').first();
    await uploadButton.click();
    await page.waitForSelector('.el-dialog, .modal', { state: 'visible' });
    
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles({
      name: 'download-test.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4 test content for download')
    });
    
    await page.click('.el-dialog__footer button:has-text("确定")');
    await page.waitForTimeout(2000);

    // 等待下载事件
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.click('.file-item:has-text("download-test") .download-btn, .file-item:has-text("download-test") button:has-text("下载")')
    ]);

    // 验证下载成功
    expect(download.suggestedFilename()).toContain('download-test');
  });

  /**
   * 测试用例：上传新版本
   * 验证能够为文件上传新版本
   */
  test('上传新版本', async ({ page }) => {
    // 先上传初始版本
    const uploadButton = page.locator('.upload-btn, button:has-text("上传")').first();
    await uploadButton.click();
    await page.waitForSelector('.el-dialog, .modal', { state: 'visible' });
    
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles({
      name: 'version-test.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4 version 1')
    });
    
    await page.click('.el-dialog__footer button:has-text("确定")');
    await page.waitForTimeout(2000);

    // 找到文件项并点击上传新版本
    const fileItem = page.locator('.file-item:has-text("version-test"), .file-card:has-text("version-test")').first();
    await fileItem.hover();

    // 点击更多操作或版本按钮
    const versionButton = fileItem.locator('.version-btn, .upload-version, button:has-text("版本"), button[title*="版本"]').first();
    if (await versionButton.isVisible().catch(() => false)) {
      await versionButton.click();
    } else {
      // 尝试点击更多菜单
      await fileItem.locator('.more-btn, .el-dropdown').first().click();
      await page.click('text=上传新版本');
    }

    // 等待上传新版本对话框
    await page.waitForSelector('.el-dialog, .modal', { state: 'visible' });

    // 选择新文件
    const newVersionInput = page.locator('input[type="file"]').first();
    await newVersionInput.setInputFiles({
      name: 'version-test.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4 version 2 updated content')
    });

    // 确认上传
    await page.click('.el-dialog__footer button:has-text("确定")');
    await page.waitForTimeout(2000);

    // 验证版本号更新
    await expect(page.locator('text=v2, text=版本 2, text=Version 2')).toBeVisible();
  });

  /**
   * 测试用例：查看版本历史
   * 验证能够查看文件的版本历史
   */
  test('查看版本历史', async ({ page }) => {
    // 先上传带版本的文件
    const uploadButton = page.locator('.upload-btn, button:has-text("上传")').first();
    await uploadButton.click();
    await page.waitForSelector('.el-dialog, .modal', { state: 'visible' });
    
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles({
      name: 'history-test.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4 history test')
    });
    
    await page.click('.el-dialog__footer button:has-text("确定")');
    await page.waitForTimeout(2000);

    // 点击文件项查看详情
    const fileItem = page.locator('.file-item:has-text("history-test"), .file-card:has-text("history-test")').first();
    await fileItem.click();

    // 等待文件详情页或版本历史显示
    await page.waitForTimeout(500);

    // 查找版本历史标签或按钮
    const historyTab = page.locator('.version-history-tab, .history-tab, button:has-text("版本历史"), button:has-text("历史")').first();
    if (await historyTab.isVisible().catch(() => false)) {
      await historyTab.click();
    }

    // 验证版本历史列表存在
    const versionList = page.locator('.version-list, .version-timeline, .history-list');
    await expect(versionList).toBeVisible();
  });

  /**
   * 测试用例：版本对比
   * 验证能够对比不同版本的文件
   */
  test('版本对比', async ({ page }) => {
    // 先上传文件并创建多个版本
    const uploadButton = page.locator('.upload-btn, button:has-text("上传")').first();
    await uploadButton.click();
    await page.waitForSelector('.el-dialog, .modal', { state: 'visible' });
    
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles({
      name: 'diff-test.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4 original content')
    });
    
    await page.click('.el-dialog__footer button:has-text("确定")');
    await page.waitForTimeout(2000);

    // 找到文件项
    const fileItem = page.locator('.file-item:has-text("diff-test"), .file-card:has-text("diff-test")').first();

    // 点击对比按钮
    const diffButton = fileItem.locator('.diff-btn, .compare-btn, button:has-text("对比"), button:has-text("Diff")').first();
    
    if (await diffButton.isVisible().catch(() => false)) {
      await diffButton.click();
    } else {
      // 通过更多菜单访问对比功能
      await fileItem.locator('.more-btn, .el-dropdown').first().click();
      await page.click('text=对比|Diff');
    }

    // 等待对比页面或对话框
    await page.waitForSelector('.diff-view, .compare-view, .el-dialog', { state: 'visible', timeout: 3000 });

    // 验证对比视图显示
    const diffView = page.locator('.diff-view, .compare-view, .el-dialog');
    await expect(diffView).toBeVisible();
  });

  /**
   * 测试用例：删除文件
   * 验证能够删除文件
   */
  test('删除文件', async ({ page }) => {
    // 先上传一个测试文件
    const uploadButton = page.locator('.upload-btn, button:has-text("上传")').first();
    await uploadButton.click();
    await page.waitForSelector('.el-dialog, .modal', { state: 'visible' });
    
    const fileName = `delete-test-${Date.now()}.pdf`;
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles({
      name: fileName,
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4 delete test')
    });
    
    await page.click('.el-dialog__footer button:has-text("确定")');
    await page.waitForTimeout(2000);

    // 找到刚上传的文件
    const fileItem = page.locator(`.file-item:has-text("delete-test"), .file-card:has-text("delete-test")`).first();
    await fileItem.hover();

    // 点击删除按钮
    const deleteButton = fileItem.locator('.delete-btn, button:has-text("删除"), [data-testid="delete-file"]').first();
    await deleteButton.click();

    // 确认删除
    await page.waitForSelector('.el-message-box, .confirm-dialog', { state: 'visible' });
    await page.click('.el-message-box__btns button:has-text("确定"), .confirm-dialog button:has-text("确定")');

    // 等待删除完成
    await page.waitForTimeout(500);

    // 验证文件已删除
    await expect(page.locator(`text=${fileName}`)).not.toBeVisible();
  });

  /**
   * 测试用例：文件预览
   * 验证能够预览文件
   */
  test('文件预览', async ({ page }) => {
    // 先上传一个测试文件
    const uploadButton = page.locator('.upload-btn, button:has-text("上传")').first();
    await uploadButton.click();
    await page.waitForSelector('.el-dialog, .modal', { state: 'visible' });
    
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles({
      name: 'preview-test.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4 preview test content')
    });
    
    await page.click('.el-dialog__footer button:has-text("确定")');
    await page.waitForTimeout(2000);

    // 点击文件名或预览按钮
    const fileItem = page.locator('.file-item:has-text("preview-test"), .file-card:has-text("preview-test")').first();
    const previewButton = fileItem.locator('.preview-btn, button:has-text("预览"), .file-name').first();
    await previewButton.click();

    // 等待预览窗口或页面
    await page.waitForTimeout(1000);

    // 验证预览组件存在
    const previewContainer = page.locator('.file-preview, .pdf-viewer, .preview-container, iframe');
    await expect(previewContainer).toBeVisible();
  });

});
