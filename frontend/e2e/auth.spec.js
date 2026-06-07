/**
 * 认证流程E2E测试
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
 * 测试套件：认证流程
 */
test.describe('认证流程测试', () => {

  /**
   * 测试用例：访问登录页面
   * 验证登录页面正常加载并显示所有必要元素
   */
  test('访问登录页面', async ({ page }) => {
    // 访问登录页面
    await page.goto(`${BASE_URL}/login`);

    // 验证页面标题
    await expect(page).toHaveTitle(/登录|Login/);

    // 验证登录表单元素存在
    await expect(page.locator('input[name="username"]')).toBeVisible();
    await expect(page.locator('input[name="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();

    // 验证页面包含登录标题
    const loginTitle = page.locator('h1, h2, .login-title');
    await expect(loginTitle).toContainText(/登录|Login/);
  });

  /**
   * 测试用例：输入错误密码显示错误
   * 验证输入错误的凭据时显示错误提示
   */
  test('输入错误密码显示错误', async ({ page }) => {
    // 访问登录页面
    await page.goto(`${BASE_URL}/login`);

    // 输入错误的用户名和密码
    await page.fill('input[name="username"]', TEST_USER.username);
    await page.fill('input[name="password"]', 'wrongpassword');

    // 点击登录按钮
    await page.click('button[type="submit"]');

    // 等待错误提示出现
    await page.waitForTimeout(500);

    // 验证错误提示显示
    const errorMessage = page.locator('.error-message, .el-message--error, [role="alert"]');
    await expect(errorMessage).toBeVisible();
    await expect(errorMessage).toContainText(/错误|失败|incorrect|failed/i);

    // 验证仍然停留在登录页面
    await expect(page).toHaveURL(/.*login.*/);
  });

  /**
   * 测试用例：成功登录后跳转
   * 验证使用正确的凭据登录后成功跳转
   */
  test('成功登录后跳转', async ({ page }) => {
    // 访问登录页面
    await page.goto(`${BASE_URL}/login`);

    // 输入正确的用户名和密码
    await page.fill('input[name="username"]', TEST_USER.username);
    await page.fill('input[name="password"]', TEST_USER.password);

    // 点击登录按钮
    await page.click('button[type="submit"]');

    // 等待登录成功并跳转
    await page.waitForURL(/.*projects|.*dashboard|.*home.*/, { timeout: 5000 });

    // 验证跳转到项目列表或首页
    await expect(page).toHaveURL(/.*projects|.*dashboard|.*home.*/);

    // 验证页面显示用户信息或欢迎语
    const userInfo = page.locator('.user-info, .username, .welcome');
    await expect(userInfo).toBeVisible();
  });

  /**
   * 测试用例：访问需要登录的页面被重定向
   * 验证未登录用户访问受保护页面时被重定向到登录页
   */
  test('访问需要登录的页面被重定向', async ({ page }) => {
    // 直接访问需要登录的页面
    await page.goto(`${BASE_URL}/projects`);

    // 等待重定向到登录页面
    await page.waitForURL(/.*login.*/, { timeout: 3000 });

    // 验证被重定向到登录页面
    await expect(page).toHaveURL(/.*login.*/);

    // 验证登录表单存在
    await expect(page.locator('input[name="username"]')).toBeVisible();
  });

  /**
   * 测试用例：登出功能
   * 验证用户能够成功登出并清除会话
   */
  test('登出功能', async ({ page }) => {
    // 先登录
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', TEST_USER.username);
    await page.fill('input[name="password"]', TEST_USER.password);
    await page.click('button[type="submit"]');
    await page.waitForURL(/.*projects|.*dashboard.*/, { timeout: 5000 });

    // 点击登出按钮或菜单
    const logoutButton = page.locator('.logout-btn, [data-testid="logout"], .el-dropdown-menu__item:has-text("退出")');
    if (await logoutButton.isVisible().catch(() => false)) {
      await logoutButton.click();
    } else {
      // 尝试通过用户菜单登出
      await page.click('.user-menu, .avatar, .el-dropdown');
      await page.click('text=退出|Logout');
    }

    // 等待登出完成并跳转到登录页
    await page.waitForURL(/.*login.*/, { timeout: 3000 });

    // 验证被重定向到登录页面
    await expect(page).toHaveURL(/.*login.*/);

    // 验证登录表单存在
    await expect(page.locator('input[name="username"]')).toBeVisible();

    // 再次尝试访问受保护页面，验证会话已清除
    await page.goto(`${BASE_URL}/projects`);
    await page.waitForURL(/.*login.*/, { timeout: 3000 });
    await expect(page).toHaveURL(/.*login.*/);
  });

  /**
   * 测试用例：记住我功能
   * 验证记住我选项能够正常工作
   */
  test('记住我功能', async ({ page, context }) => {
    // 访问登录页面
    await page.goto(`${BASE_URL}/login`);

    // 输入凭据并勾选记住我
    await page.fill('input[name="username"]', TEST_USER.username);
    await page.fill('input[name="password"]', TEST_USER.password);
    
    // 勾选记住我（如果存在）
    const rememberMe = page.locator('input[type="checkbox"][name="remember"], .remember-me input');
    if (await rememberMe.isVisible().catch(() => false)) {
      await rememberMe.check();
    }

    // 登录
    await page.click('button[type="submit"]');
    await page.waitForURL(/.*projects|.*dashboard.*/, { timeout: 5000 });

    // 获取cookies
    const cookies = await context.cookies();
    const authCookie = cookies.find(c => c.name.includes('token') || c.name.includes('auth') || c.name.includes('session'));
    
    // 验证存在认证cookie且有过期时间（记住我功能）
    expect(authCookie).toBeDefined();
    if (authCookie && authCookie.expires) {
      expect(authCookie.expires).toBeGreaterThan(Date.now() / 1000);
    }
  });

  /**
   * 测试用例：表单验证
   * 验证登录表单的输入验证
   */
  test('登录表单验证', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);

    // 测试空表单提交
    await page.click('button[type="submit"]');
    
    // 验证显示必填字段提示
    const validationMessage = page.locator('.el-form-item__error, .error-message, [role="alert"]');
    await expect(validationMessage.first()).toBeVisible();

    // 测试用户名最小长度
    await page.fill('input[name="username"]', 'ab');
    await page.fill('input[name="password"]', 'short');
    await page.click('button[type="submit"]');
    
    // 验证仍然显示验证错误
    await expect(validationMessage.first()).toBeVisible();
  });

});
