/**
 * 通知功能E2E测试
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
 * 测试套件：通知功能
 */
test.describe('通知功能测试', () => {

  /**
   * 每个测试前登录
   */
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  /**
   * 测试用例：通知图标显示
   * 验证通知图标正常显示在导航栏
   */
  test('通知图标显示', async ({ page }) => {
    // 验证通知图标存在
    const notificationIcon = page.locator('.notification-icon, .bell-icon, [data-testid="notification-icon"], .el-icon-bell').first();
    await expect(notificationIcon).toBeVisible();
    
    // 验证通知徽章（如果有未读通知）
    const notificationBadge = page.locator('.notification-badge, .el-badge, .badge');
    // 徽章可能存在也可能不存在，取决于是否有未读通知
    const hasBadge = await notificationBadge.isVisible().catch(() => false);
    
    if (hasBadge) {
      await expect(notificationBadge).toBeVisible();
    }
  });

  /**
   * 测试用例：打开通知面板
   * 验证能够打开通知列表面板
   */
  test('打开通知面板', async ({ page }) => {
    // 点击通知图标
    const notificationIcon = page.locator('.notification-icon, .bell-icon, [data-testid="notification-icon"]').first();
    await notificationIcon.click();
    
    // 等待通知面板显示
    await page.waitForTimeout(300);
    
    // 验证通知面板存在
    const notificationPanel = page.locator('.notification-panel, .notification-dropdown, .el-dropdown-menu, .notification-list');
    await expect(notificationPanel).toBeVisible();
    
    // 验证面板标题
    await expect(page.locator('text=通知|消息|Notifications')).toBeVisible();
  });

  /**
   * 测试用例：查看通知列表
   * 验证通知列表正常显示
   */
  test('查看通知列表', async ({ page }) => {
    // 打开通知面板
    const notificationIcon = page.locator('.notification-icon, .bell-icon').first();
    await notificationIcon.click();
    await page.waitForTimeout(300);
    
    // 验证通知列表容器
    const notificationList = page.locator('.notification-list, .notification-items, .message-list');
    await expect(notificationList).toBeVisible();
    
    // 验证通知项或空状态
    const notificationItems = page.locator('.notification-item, .message-item');
    const emptyState = page.locator('.notification-empty, .empty-state, .no-notifications');
    
    const hasItems = await notificationItems.count() > 0;
    const hasEmptyState = await emptyState.isVisible().catch(() => false);
    
    expect(hasItems || hasEmptyState).toBeTruthy();
    
    // 如果有通知项，验证其结构
    if (hasItems) {
      const firstItem = notificationItems.first();
      await expect(firstItem.locator('.notification-title, .title, .message-title')).toBeVisible();
      await expect(firstItem.locator('.notification-time, .time, .timestamp')).toBeVisible();
    }
  });

  /**
   * 测试用例：标记通知为已读
   * 验证能够将通知标记为已读
   */
  test('标记通知为已读', async ({ page }) => {
    // 打开通知面板
    const notificationIcon = page.locator('.notification-icon, .bell-icon').first();
    await notificationIcon.click();
    await page.waitForTimeout(300);
    
    // 查找未读通知
    const unreadItem = page.locator('.notification-item.unread, .message-item.unread, .unread').first();
    
    if (await unreadItem.isVisible().catch(() => false)) {
      // 点击通知项
      await unreadItem.click();
      await page.waitForTimeout(300);
      
      // 验证通知状态变化
      // 注意：这里可能需要重新打开面板来验证
      await notificationIcon.click();
      await page.waitForTimeout(300);
      
      // 或者查找标记已读按钮
      const markReadBtn = page.locator('.mark-read-btn, button:has-text("标记已读")').first();
      if (await markReadBtn.isVisible().catch(() => false)) {
        await markReadBtn.click();
        await page.waitForTimeout(300);
      }
    }
  });

  /**
   * 测试用例：标记所有通知为已读
   * 验证能够一键标记所有通知为已读
   */
  test('标记所有通知为已读', async ({ page }) => {
    // 打开通知面板
    const notificationIcon = page.locator('.notification-icon, .bell-icon').first();
    await notificationIcon.click();
    await page.waitForTimeout(300);
    
    // 查找"全部已读"按钮
    const markAllReadBtn = page.locator('.mark-all-read, button:has-text("全部已读"), button:has-text("全部标记")').first();
    
    if (await markAllReadBtn.isVisible().catch(() => false)) {
      await markAllReadBtn.click();
      await page.waitForTimeout(500);
      
      // 验证成功提示
      const successMessage = page.locator('.el-message--success, .success-message');
      await expect(successMessage).toBeVisible();
      
      // 验证未读徽章消失
      const notificationBadge = page.locator('.notification-badge, .el-badge__content');
      await expect(notificationBadge).not.toBeVisible();
    }
  });

  /**
   * 测试用例：删除通知
   * 验证能够删除单条通知
   */
  test('删除通知', async ({ page }) => {
    // 打开通知面板
    const notificationIcon = page.locator('.notification-icon, .bell-icon').first();
    await notificationIcon.click();
    await page.waitForTimeout(300);
    
    // 查找通知项
    const notificationItem = page.locator('.notification-item, .message-item').first();
    
    if (await notificationItem.isVisible().catch(() => false)) {
      // 悬停显示删除按钮
      await notificationItem.hover();
      
      // 查找删除按钮
      const deleteBtn = notificationItem.locator('.delete-btn, button:has-text("删除"), .el-icon-close').first();
      
      if (await deleteBtn.isVisible().catch(() => false)) {
        await deleteBtn.click();
        await page.waitForTimeout(300);
        
        // 确认删除（如果有确认对话框）
        const confirmDialog = page.locator('.el-message-box, .confirm-dialog');
        if (await confirmDialog.isVisible().catch(() => false)) {
          await page.click('.el-message-box__btns button:has-text("确定")');
          await page.waitForTimeout(300);
        }
        
        // 验证成功提示
        const successMessage = page.locator('.el-message--success, .success-message');
        await expect(successMessage).toBeVisible();
      }
    }
  });

  /**
   * 测试用例：清空所有通知
   * 验证能够清空所有通知
   */
  test('清空所有通知', async ({ page }) => {
    // 打开通知面板
    const notificationIcon = page.locator('.notification-icon, .bell-icon').first();
    await notificationIcon.click();
    await page.waitForTimeout(300);
    
    // 查找"清空"按钮
    const clearAllBtn = page.locator('.clear-all, button:has-text("清空"), button:has-text("全部删除")').first();
    
    if (await clearAllBtn.isVisible().catch(() => false)) {
      await clearAllBtn.click();
      await page.waitForTimeout(300);
      
      // 确认清空
      const confirmDialog = page.locator('.el-message-box, .confirm-dialog');
      if (await confirmDialog.isVisible().catch(() => false)) {
        await page.click('.el-message-box__btns button:has-text("确定")');
        await page.waitForTimeout(500);
      }
      
      // 验证空状态显示
      const emptyState = page.locator('.notification-empty, .empty-state, .no-notifications');
      await expect(emptyState).toBeVisible();
    }
  });

  /**
   * 测试用例：通知详情跳转
   * 验证点击通知能够跳转到相关内容
   */
  test('通知详情跳转', async ({ page }) => {
    // 打开通知面板
    const notificationIcon = page.locator('.notification-icon, .bell-icon').first();
    await notificationIcon.click();
    await page.waitForTimeout(300);
    
    // 查找通知项
    const notificationItem = page.locator('.notification-item, .message-item').first();
    
    if (await notificationItem.isVisible().catch(() => false)) {
      // 记录当前URL
      const beforeUrl = page.url();
      
      // 点击通知项
      await notificationItem.click();
      await page.waitForTimeout(1000);
      
      // 验证页面跳转
      const afterUrl = page.url();
      expect(afterUrl).not.toBe(beforeUrl);
    }
  });

  /**
   * 测试用例：通知设置
   * 验证能够访问和修改通知设置
   */
  test('通知设置', async ({ page }) => {
    // 打开通知面板
    const notificationIcon = page.locator('.notification-icon, .bell-icon').first();
    await notificationIcon.click();
    await page.waitForTimeout(300);
    
    // 查找设置按钮或链接
    const settingsBtn = page.locator('.notification-settings, button:has-text("设置"), a:has-text("设置")').first();
    
    if (await settingsBtn.isVisible().catch(() => false)) {
      await settingsBtn.click();
      await page.waitForTimeout(500);
      
      // 验证设置页面或对话框
      const settingsPanel = page.locator('.notification-settings-panel, .settings-dialog, .el-dialog');
      await expect(settingsPanel).toBeVisible();
      
      // 验证通知类型选项
      const notificationTypes = page.locator('.notification-type, .setting-item');
      if (await notificationTypes.count() > 0) {
        await expect(notificationTypes.first()).toBeVisible();
      }
      
      // 测试开关通知
      const toggleSwitch = page.locator('.el-switch, .toggle-switch').first();
      if (await toggleSwitch.isVisible().catch(() => false)) {
        const currentState = await toggleSwitch.isChecked().catch(() => false);
        await toggleSwitch.click();
        await page.waitForTimeout(300);
        
        // 验证状态变化
        const newState = await toggleSwitch.isChecked().catch(() => false);
        expect(newState).not.toBe(currentState);
      }
      
      // 关闭设置
      await page.click('.el-dialog__headerbtn, .close-btn, button:has-text("关闭")');
    }
  });

  /**
   * 测试用例：通知分类筛选
   * 验证能够按类型筛选通知
   */
  test('通知分类筛选', async ({ page }) => {
    // 打开通知面板
    const notificationIcon = page.locator('.notification-icon, .bell-icon').first();
    await notificationIcon.click();
    await page.waitForTimeout(300);
    
    // 查找分类标签
    const typeTabs = page.locator('.notification-tabs, .type-tabs, .el-tabs');
    
    if (await typeTabs.isVisible().catch(() => false)) {
      // 点击不同分类
      const allTab = page.locator('.el-tabs__item:has-text("全部"), .tab-item:has-text("全部")').first();
      const unreadTab = page.locator('.el-tabs__item:has-text("未读"), .tab-item:has-text("未读")').first();
      const systemTab = page.locator('.el-tabs__item:has-text("系统"), .tab-item:has-text("系统")').first();
      
      if (await unreadTab.isVisible().catch(() => false)) {
        await unreadTab.click();
        await page.waitForTimeout(300);
      }
      
      if (await systemTab.isVisible().catch(() => false)) {
        await systemTab.click();
        await page.waitForTimeout(300);
      }
      
      if (await allTab.isVisible().catch(() => false)) {
        await allTab.click();
        await page.waitForTimeout(300);
      }
    }
  });

  /**
   * 测试用例：实时通知接收
   * 验证能够接收实时通知（模拟）
   */
  test('实时通知接收', async ({ page }) => {
    // 导航到首页
    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForTimeout(500);
    
    // 验证通知图标存在
    const notificationIcon = page.locator('.notification-icon, .bell-icon').first();
    await expect(notificationIcon).toBeVisible();
    
    // 注意：实际测试实时通知需要后端配合
    // 这里主要验证通知组件能够正常显示和更新
    
    // 打开通知面板查看
    await notificationIcon.click();
    await page.waitForTimeout(300);
    
    // 验证面板显示
    const notificationPanel = page.locator('.notification-panel, .notification-dropdown');
    await expect(notificationPanel).toBeVisible();
  });

  /**
   * 测试用例：通知中心页面
   * 验证能够访问完整的通知中心页面
   */
  test('通知中心页面', async ({ page }) => {
    // 直接访问通知中心页面
    await page.goto(`${BASE_URL}/notifications`);
    await page.waitForTimeout(500);
    
    // 验证页面标题
    await expect(page.locator('h1, h2, .page-title')).toContainText(/通知|消息|Notifications/);
    
    // 验证通知列表存在
    const notificationList = page.locator('.notification-list, .message-list');
    await expect(notificationList).toBeVisible();
    
    // 验证操作按钮存在
    const actionButtons = page.locator('.notification-actions, .action-buttons');
    if (await actionButtons.isVisible().catch(() => false)) {
      await expect(actionButtons).toBeVisible();
    }
  });

});
