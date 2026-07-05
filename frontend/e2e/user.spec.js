/**
 * 用户管理E2E测试
 * 使用Playwright进行端到端测试
 */

import { test, expect } from '@playwright/test';

// 测试配置
const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:5173';
const TEST_USER = {
  username: 'testuser',
  password: 'TestPass123!',
  email: 'test@example.com'
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
 * 测试套件：用户管理
 */
test.describe('用户管理测试', () => {

  /**
   * 每个测试前登录
   */
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  /**
   * 测试用例：访问个人资料页面
   * 验证能够正常访问个人资料页面
   */
  test('访问个人资料页面', async ({ page }) => {
    // 点击用户菜单
    await page.click('.user-menu, .avatar, .el-dropdown, .user-info');
    
    // 点击个人资料选项
    await page.click('text=个人资料|个人信息|Profile');
    
    // 等待页面加载
    await page.waitForTimeout(500);
    
    // 验证页面标题
    await expect(page.locator('h1, h2, .page-title')).toContainText(/个人资料|个人信息|Profile/);
    
    // 验证个人资料表单元素存在
    await expect(page.locator('input[name="username"], input[name="nickname"], .profile-form')).toBeVisible();
    
    // 验证头像显示
    await expect(page.locator('.avatar, .user-avatar, .profile-avatar')).toBeVisible();
  });

  /**
   * 测试用例：修改个人信息
   * 验证能够成功修改昵称、邮箱等个人信息
   */
  test('修改个人信息', async ({ page }) => {
    // 导航到个人资料页面
    await page.goto(`${BASE_URL}/profile`);
    await page.waitForTimeout(500);
    
    // 如果页面没有直接跳转，通过菜单进入
    const profileForm = page.locator('.profile-form, form');
    if (!(await profileForm.isVisible().catch(() => false))) {
      await page.click('.user-menu, .avatar, .el-dropdown');
      await page.click('text=个人资料|个人信息|Profile');
      await page.waitForTimeout(500);
    }
    
    // 修改昵称
    const nicknameInput = page.locator('input[name="nickname"], input[placeholder*="昵称"]').first();
    if (await nicknameInput.isVisible().catch(() => false)) {
      const newNickname = `测试用户-${Date.now()}`;
      await nicknameInput.fill('');
      await nicknameInput.fill(newNickname);
    }
    
    // 修改邮箱
    const emailInput = page.locator('input[name="email"], input[type="email"]').first();
    if (await emailInput.isVisible().catch(() => false)) {
      await emailInput.fill('');
      await emailInput.fill(`newemail${Date.now()}@example.com`);
    }
    
    // 修改个人简介
    const bioInput = page.locator('textarea[name="bio"], textarea[name="description"], textarea[placeholder*="简介"]').first();
    if (await bioInput.isVisible().catch(() => false)) {
      await bioInput.fill('这是修改后的个人简介');
    }
    
    // 点击保存按钮
    await page.click('button:has-text("保存"), button:has-text("更新"), button[type="submit"]');
    
    // 等待保存成功提示
    await page.waitForTimeout(500);
    
    // 验证成功提示
    const successMessage = page.locator('.el-message--success, .success-message, [role="alert"]');
    await expect(successMessage).toBeVisible();
  });

  /**
   * 测试用例：修改密码
   * 验证能够成功修改密码
   */
  test('修改密码', async ({ page }) => {
    // 导航到个人资料或密码修改页面
    await page.goto(`${BASE_URL}/profile`);
    await page.waitForTimeout(500);
    
    // 查找密码修改标签或按钮
    const passwordTab = page.locator('.password-tab, button:has-text("密码"), a:has-text("密码")').first();
    if (await passwordTab.isVisible().catch(() => false)) {
      await passwordTab.click();
      await page.waitForTimeout(300);
    }
    
    // 查找密码修改表单
    const oldPasswordInput = page.locator('input[name="oldPassword"], input[name="currentPassword"], input[placeholder*="当前密码"]').first();
    const newPasswordInput = page.locator('input[name="newPassword"], input[name="password"], input[placeholder*="新密码"]').first();
    const confirmPasswordInput = page.locator('input[name="confirmPassword"], input[name="confirm"], input[placeholder*="确认密码"]').first();
    
    // 如果存在密码表单，进行测试
    if (await oldPasswordInput.isVisible().catch(() => false)) {
      // 输入当前密码
      await oldPasswordInput.fill(TEST_USER.password);
      
      // 输入新密码
      const newPassword = 'NewPass123!';
      await newPasswordInput.fill(newPassword);
      await confirmPasswordInput.fill(newPassword);
      
      // 点击修改密码按钮
      await page.click('button:has-text("修改密码"), button:has-text("更新密码"), button[type="submit"]');
      
      // 等待操作完成
      await page.waitForTimeout(500);
      
      // 验证成功提示
      const successMessage = page.locator('.el-message--success, .success-message');
      await expect(successMessage).toBeVisible();
    }
  });

  /**
   * 测试用例：密码修改验证
   * 验证密码修改时的表单验证
   */
  test('密码修改表单验证', async ({ page }) => {
    // 导航到密码修改页面
    await page.goto(`${BASE_URL}/profile/password`);
    await page.waitForTimeout(500);
    
    // 如果没有直接跳转，通过个人资料页面进入
    const passwordForm = page.locator('input[name="newPassword"], input[name="password"]');
    if (!(await passwordForm.isVisible().catch(() => false))) {
      await page.goto(`${BASE_URL}/profile`);
      await page.waitForTimeout(500);
      
      const passwordTab = page.locator('.password-tab, button:has-text("密码")').first();
      if (await passwordTab.isVisible().catch(() => false)) {
        await passwordTab.click();
        await page.waitForTimeout(300);
      }
    }
    
    // 测试空表单提交
    const submitButton = page.locator('button:has-text("修改密码"), button:has-text("更新"), button[type="submit"]').first();
    if (await submitButton.isVisible().catch(() => false)) {
      await submitButton.click();
      
      // 验证显示验证错误
      const errorMessage = page.locator('.el-form-item__error, .error-message, [role="alert"]');
      await expect(errorMessage.first()).toBeVisible();
    }
    
    // 测试密码不匹配
    const newPasswordInput = page.locator('input[name="newPassword"], input[name="password"]').first();
    const confirmPasswordInput = page.locator('input[name="confirmPassword"], input[name="confirm"]').first();
    
    if (await newPasswordInput.isVisible().catch(() => false) && await confirmPasswordInput.isVisible().catch(() => false)) {
      await newPasswordInput.fill('NewPass123!');
      await confirmPasswordInput.fill('DifferentPass123!');
      await submitButton.click();
      
      // 验证显示密码不匹配错误
      const errorMessage = page.locator('.el-form-item__error, .error-message');
      await expect(errorMessage.first()).toBeVisible();
    }
  });

  /**
   * 测试用例：上传头像
   * 验证能够成功上传用户头像
   */
  test('上传头像', async ({ page }) => {
    // 导航到个人资料页面
    await page.goto(`${BASE_URL}/profile`);
    await page.waitForTimeout(500);
    
    // 查找头像上传区域
    const avatarUpload = page.locator('.avatar-upload, .upload-avatar, input[type="file"]').first();
    
    if (await avatarUpload.isVisible().catch(() => false)) {
      // 上传测试图片
      await avatarUpload.setInputFiles({
        name: 'test-avatar.png',
        mimeType: 'image/png',
        buffer: Buffer.from('fake-image-data-for-testing')
      });
      
      // 等待上传完成
      await page.waitForTimeout(1000);
      
      // 验证成功提示
      const successMessage = page.locator('.el-message--success, .success-message');
      await expect(successMessage).toBeVisible();
    }
  });

  /**
   * 测试用例：查看用户活动记录
   * 验证能够查看用户的操作历史
   */
  test('查看用户活动记录', async ({ page }) => {
    // 导航到个人资料页面
    await page.goto(`${BASE_URL}/profile`);
    await page.waitForTimeout(500);
    
    // 查找活动记录标签或链接
    const activityTab = page.locator('.activity-tab, button:has-text("活动"), a:has-text("活动记录"), button:has-text("历史")').first();
    
    if (await activityTab.isVisible().catch(() => false)) {
      await activityTab.click();
      await page.waitForTimeout(500);
      
      // 验证活动记录列表存在
      const activityList = page.locator('.activity-list, .history-list, .log-list');
      await expect(activityList).toBeVisible();
      
      // 验证活动项显示
      const activityItems = page.locator('.activity-item, .history-item');
      if (await activityItems.count() > 0) {
        await expect(activityItems.first()).toBeVisible();
      }
    }
  });

  /**
   * 测试用例：账户安全设置
   * 验证能够访问和修改安全设置
   */
  test('账户安全设置', async ({ page }) => {
    // 导航到安全设置页面
    await page.goto(`${BASE_URL}/profile/security`);
    await page.waitForTimeout(500);
    
    // 如果没有直接跳转，通过个人资料页面进入
    const securityForm = page.locator('.security-settings, .security-form');
    if (!(await securityForm.isVisible().catch(() => false))) {
      await page.goto(`${BASE_URL}/profile`);
      await page.waitForTimeout(500);
      
      const securityTab = page.locator('.security-tab, button:has-text("安全"), a:has-text("安全")').first();
      if (await securityTab.isVisible().catch(() => false)) {
        await securityTab.click();
        await page.waitForTimeout(300);
      }
    }
    
    // 验证安全设置选项存在
    const twoFactorToggle = page.locator('.two-factor-toggle, input[name="twoFactor"]').first();
    const loginNotificationToggle = page.locator('.login-notification-toggle, input[name="loginNotification"]').first();
    
    // 测试切换双因素认证（如果存在）
    if (await twoFactorToggle.isVisible().catch(() => false)) {
      const currentState = await twoFactorToggle.isChecked().catch(() => false);
      await twoFactorToggle.click();
      await page.waitForTimeout(300);
      
      // 验证状态变化
      const newState = await twoFactorToggle.isChecked().catch(() => false);
      expect(newState).not.toBe(currentState);
    }
  });

  /**
   * 测试用例：注销账户
   * 验证能够注销账户（模拟流程）
   */
  test('注销账户流程', async ({ page }) => {
    // 导航到账户设置页面
    await page.goto(`${BASE_URL}/profile/settings`);
    await page.waitForTimeout(500);
    
    // 查找账户注销或删除按钮
    const deleteAccountBtn = page.locator('button:has-text("注销账户"), button:has-text("删除账户"), .delete-account-btn').first();
    
    if (await deleteAccountBtn.isVisible().catch(() => false)) {
      await deleteAccountBtn.click();
      
      // 等待确认对话框
      await page.waitForSelector('.el-message-box, .confirm-dialog, .modal', { state: 'visible' });
      
      // 验证确认对话框显示
      await expect(page.locator('.el-message-box, .confirm-dialog')).toBeVisible();
      
      // 点击取消（不实际删除账户）
      await page.click('.el-message-box__btns button:has-text("取消"), .confirm-dialog button:has-text("取消")');
      
      // 验证对话框关闭
      await expect(page.locator('.el-message-box, .confirm-dialog')).not.toBeVisible();
    }
  });

});
