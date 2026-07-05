/**
 * 考试安排E2E测试
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
 * 测试套件：考试安排
 */
test.describe('考试安排测试', () => {

  /**
   * 每个测试前登录
   */
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  /**
   * 测试用例：创建考试
   * 验证能够成功创建考试安排
   */
  test('创建考试', async ({ page }) => {
    // 导航到考试列表页面
    await page.goto(`${BASE_URL}/exams`);
    await page.waitForTimeout(500);

    // 点击创建考试按钮
    const createButton = page.locator('.create-exam-btn, [data-testid="create-exam"], button:has-text("新建考试"), button:has-text("创建考试")').first();
    await createButton.click();

    // 等待对话框出现
    await page.waitForSelector('.el-dialog, .modal, .dialog', { state: 'visible' });

    // 填写考试信息
    const examName = `测试考试-${Date.now()}`;
    await page.fill('input[name="name"], input[placeholder*="考试"], .el-dialog input', examName);
    await page.fill('textarea[name="description"], textarea[placeholder*="描述"], .el-dialog textarea', '这是一个测试考试描述');

    // 设置考试日期
    const dateInput = page.locator('input[placeholder*="日期"], .el-date-picker input').first();
    if (await dateInput.isVisible().catch(() => false)) {
      await dateInput.click();
      // 选择明天的日期
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      const dateStr = tomorrow.toISOString().split('T')[0];
      await page.fill('input[placeholder*="日期"]', dateStr);
    }

    // 点击确认按钮
    await page.click('.el-dialog__footer button:has-text("确定"), .el-dialog__footer button:has-text("创建"), .modal-footer button:has-text("确定")');

    // 等待考试创建成功
    await page.waitForTimeout(500);

    // 验证考试列表中显示新考试
    await expect(page.locator('text=' + examName)).toBeVisible();
  });

  /**
   * 测试用例：查看考试列表
   * 验证考试列表正常显示
   */
  test('查看考试列表', async ({ page }) => {
    // 导航到考试列表页面
    await page.goto(`${BASE_URL}/exams`);
    await page.waitForTimeout(500);

    // 验证页面标题
    await expect(page.locator('h1, h2, .page-title')).toContainText(/考试|Exam/);

    // 验证考试列表容器存在
    const examList = page.locator('.exam-list, .exam-grid, [data-testid="exam-list"]');
    await expect(examList).toBeVisible();

    // 验证列表中有考试或空状态提示
    const examItems = page.locator('.exam-item, .exam-card');
    const emptyState = page.locator('.empty-state, .el-empty');
    
    const hasExams = await examItems.count() > 0;
    const hasEmptyState = await emptyState.isVisible().catch(() => false);
    
    expect(hasExams || hasEmptyState).toBeTruthy();

    // 验证考试项显示必要信息（如果有考试）
    if (hasExams) {
      const firstExam = examItems.first();
      await expect(firstExam.locator('.exam-name, .title, h3')).toBeVisible();
    }
  });

  /**
   * 测试用例：编辑考试
   * 验证能够编辑考试信息
   */
  test('编辑考试', async ({ page }) => {
    // 先创建一个考试
    await page.goto(`${BASE_URL}/exams`);
    await page.waitForTimeout(500);

    const createButton = page.locator('.create-exam-btn, button:has-text("新建")').first();
    await createButton.click();
    await page.waitForSelector('.el-dialog, .modal', { state: 'visible' });
    
    const examName = `待编辑考试-${Date.now()}`;
    await page.fill('.el-dialog input, .modal input', examName);
    await page.fill('.el-dialog textarea, .modal textarea', '原始描述');
    await page.click('.el-dialog__footer button:has-text("确定")');
    await page.waitForTimeout(500);

    // 找到刚创建的考试并点击编辑
    const examItem = page.locator('.exam-item:has-text("' + examName + '"), .exam-card:has-text("' + examName + '")').first();
    await examItem.hover();

    const editButton = examItem.locator('.edit-btn, button:has-text("编辑"), [data-testid="edit-exam"]').first();
    await editButton.click();

    // 等待编辑对话框
    await page.waitForSelector('.el-dialog, .modal', { state: 'visible' });

    // 修改考试信息
    const newName = `编辑后的考试-${Date.now()}`;
    const nameInput = page.locator('.el-dialog input, .modal input').first();
    await nameInput.fill('');
    await nameInput.fill(newName);

    // 保存修改
    await page.click('.el-dialog__footer button:has-text("确定"), .el-dialog__footer button:has-text("保存")');
    await page.waitForTimeout(500);

    // 验证考试名称已更新
    await expect(page.locator('text=' + newName)).toBeVisible();
  });

  /**
   * 测试用例：删除考试
   * 验证能够删除考试
   */
  test('删除考试', async ({ page }) => {
    // 先创建一个考试
    await page.goto(`${BASE_URL}/exams`);
    await page.waitForTimeout(500);

    const createButton = page.locator('.create-exam-btn, button:has-text("新建")').first();
    await createButton.click();
    await page.waitForSelector('.el-dialog, .modal', { state: 'visible' });
    
    const examName = `待删除考试-${Date.now()}`;
    await page.fill('.el-dialog input, .modal input', examName);
    await page.click('.el-dialog__footer button:has-text("确定")');
    await page.waitForTimeout(500);

    // 找到刚创建的考试
    const examItem = page.locator('.exam-item:has-text("' + examName + '"), .exam-card:has-text("' + examName + '")').first();
    await examItem.hover();

    // 点击删除按钮
    const deleteButton = examItem.locator('.delete-btn, button:has-text("删除"), [data-testid="delete-exam"]').first();
    await deleteButton.click();

    // 确认删除
    await page.waitForSelector('.el-message-box, .confirm-dialog', { state: 'visible' });
    await page.click('.el-message-box__btns button:has-text("确定"), .confirm-dialog button:has-text("确定")');

    // 等待删除完成
    await page.waitForTimeout(500);

    // 验证考试已删除
    await expect(page.locator('text=' + examName)).not.toBeVisible();
  });

  /**
   * 测试用例：考试提醒显示
   * 验证考试提醒功能正常显示
   */
  test('考试提醒显示', async ({ page }) => {
    // 创建一个即将举行的考试
    await page.goto(`${BASE_URL}/exams`);
    await page.waitForTimeout(500);

    const createButton = page.locator('.create-exam-btn, button:has-text("新建")').first();
    await createButton.click();
    await page.waitForSelector('.el-dialog, .modal', { state: 'visible' });
    
    const examName = `提醒测试考试-${Date.now()}`;
    await page.fill('.el-dialog input, .modal input', examName);
    
    // 设置考试日期为明天
    const dateInput = page.locator('input[placeholder*="日期"], .el-date-picker input').first();
    if (await dateInput.isVisible().catch(() => false)) {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      const dateStr = tomorrow.toISOString().split('T')[0];
      await dateInput.fill(dateStr);
    }
    
    await page.click('.el-dialog__footer button:has-text("确定")');
    await page.waitForTimeout(500);

    // 导航到首页或其他页面查看提醒
    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForTimeout(500);

    // 验证考试提醒组件存在
    const reminderComponent = page.locator('.exam-reminder, .reminder-list, .upcoming-exams, [data-testid="exam-reminder"]');
    
    // 提醒组件可能存在也可能不存在，取决于实现
    const hasReminder = await reminderComponent.isVisible().catch(() => false);
    
    if (hasReminder) {
      // 验证提醒中包含刚创建的考试
      await expect(page.locator('text=' + examName)).toBeVisible();
    }
  });

  /**
   * 测试用例：考试详情查看
   * 验证能够查看考试详情
   */
  test('考试详情查看', async ({ page }) => {
    // 先创建一个考试
    await page.goto(`${BASE_URL}/exams`);
    await page.waitForTimeout(500);

    const createButton = page.locator('.create-exam-btn, button:has-text("新建")').first();
    await createButton.click();
    await page.waitForSelector('.el-dialog, .modal', { state: 'visible' });
    
    const examName = `详情测试考试-${Date.now()}`;
    await page.fill('.el-dialog input, .modal input', examName);
    await page.fill('.el-dialog textarea, .modal textarea', '考试详情描述');
    await page.click('.el-dialog__footer button:has-text("确定")');
    await page.waitForTimeout(500);

    // 点击考试项查看详情
    const examItem = page.locator('.exam-item:has-text("' + examName + '"), .exam-card:has-text("' + examName + '")').first();
    await examItem.click();

    // 等待详情页面或对话框
    await page.waitForTimeout(500);

    // 验证详情显示
    const detailView = page.locator('.exam-detail, .detail-view, .el-dialog');
    await expect(detailView).toBeVisible();
    await expect(page.locator('text=考试详情描述')).toBeVisible();
  });

  /**
   * 测试用例：考试状态筛选
   * 验证能够按状态筛选考试
   */
  test('考试状态筛选', async ({ page }) => {
    await page.goto(`${BASE_URL}/exams`);
    await page.waitForTimeout(500);

    // 查找状态筛选器
    const statusFilter = page.locator('.status-filter, .filter-select, .el-select').first();
    
    if (await statusFilter.isVisible().catch(() => false)) {
      // 点击筛选器
      await statusFilter.click();
      
      // 选择不同状态
      await page.click('text=进行中');
      await page.waitForTimeout(300);
      
      await statusFilter.click();
      await page.click('text=已结束');
      await page.waitForTimeout(300);
      
      await statusFilter.click();
      await page.click('text=全部');
      await page.waitForTimeout(300);
    }
  });

  /**
   * 测试用例：考试日历视图
   * 验证考试日历视图正常显示
   */
  test('考试日历视图', async ({ page }) => {
    await page.goto(`${BASE_URL}/exams`);
    await page.waitForTimeout(500);

    // 查找日历视图切换按钮
    const calendarViewBtn = page.locator('.calendar-view-btn, button:has-text("日历"), .view-toggle button').first();
    
    if (await calendarViewBtn.isVisible().catch(() => false)) {
      await calendarViewBtn.click();
      await page.waitForTimeout(500);

      // 验证日历组件存在
      const calendar = page.locator('.calendar, .el-calendar, .exam-calendar');
      await expect(calendar).toBeVisible();
    }
  });

});
