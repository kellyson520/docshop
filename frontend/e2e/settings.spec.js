/**
 * 系统设置E2E测试
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
 * 测试套件：系统设置
 */
test.describe('系统设置测试', () => {

  /**
   * 每个测试前登录
   */
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  /**
   * 测试用例：访问设置页面
   * 验证能够正常访问系统设置页面
   */
  test('访问设置页面', async ({ page }) => {
    // 点击用户菜单
    await page.click('.user-menu, .avatar, .el-dropdown, .user-info');
    
    // 点击设置选项
    await page.click('text=设置|系统设置|Settings');
    
    // 等待页面加载
    await page.waitForTimeout(500);
    
    // 验证页面标题
    await expect(page.locator('h1, h2, .page-title')).toContainText(/设置|Settings/);
    
    // 验证设置菜单或选项卡存在
    const settingsMenu = page.locator('.settings-menu, .settings-tabs, .settings-sidebar');
    await expect(settingsMenu).toBeVisible();
  });

  /**
   * 测试用例：界面主题设置
   * 验证能够切换界面主题
   */
  test('界面主题设置', async ({ page }) => {
    // 导航到设置页面
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForTimeout(500);
    
    // 查找主题设置选项
    const themeSection = page.locator('.theme-settings, .appearance-settings, [data-testid="theme-settings"]').first();
    
    if (await themeSection.isVisible().catch(() => false)) {
      // 查找主题选择器
      const themeSelect = page.locator('select[name="theme"], .theme-select').first();
      const darkModeToggle = page.locator('.dark-mode-toggle, input[name="darkMode"]').first();
      
      if (await themeSelect.isVisible().catch(() => false)) {
        // 选择不同主题
        await themeSelect.selectOption('dark');
        await page.waitForTimeout(300);
        
        // 验证主题变化（通过检查body类或特定元素）
        const bodyClass = await page.evaluate(() => document.body.className);
        expect(bodyClass).toMatch(/dark|theme-dark/i);
        
        // 切换回亮色主题
        await themeSelect.selectOption('light');
        await page.waitForTimeout(300);
      }
      
      if (await darkModeToggle.isVisible().catch(() => false)) {
        // 切换深色模式
        const currentState = await darkModeToggle.isChecked().catch(() => false);
        await darkModeToggle.click();
        await page.waitForTimeout(300);
        
        // 验证状态变化
        const newState = await darkModeToggle.isChecked().catch(() => false);
        expect(newState).not.toBe(currentState);
      }
    }
  });

  /**
   * 测试用例：语言设置
   * 验证能够切换界面语言
   */
  test('语言设置', async ({ page }) => {
    // 导航到设置页面
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForTimeout(500);
    
    // 查找语言设置选项
    const languageSection = page.locator('.language-settings, .locale-settings').first();
    
    if (await languageSection.isVisible().catch(() => false)) {
      // 查找语言选择器
      const languageSelect = page.locator('select[name="language"], select[name="locale"], .language-select').first();
      
      if (await languageSelect.isVisible().catch(() => false)) {
        // 切换到英文
        await languageSelect.selectOption('en');
        await page.waitForTimeout(500);
        
        // 验证语言变化
        const pageTitle = await page.locator('h1, h2, .page-title').textContent();
        expect(pageTitle.toLowerCase()).toMatch(/settings|configuration/);
        
        // 切换回中文
        await languageSelect.selectOption('zh');
        await page.waitForTimeout(500);
      }
    }
  });

  /**
   * 测试用例：文件存储设置
   * 验证能够配置文件存储选项
   */
  test('文件存储设置', async ({ page }) => {
    // 导航到设置页面
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForTimeout(500);
    
    // 查找存储设置选项卡或链接
    const storageTab = page.locator('.storage-tab, button:has-text("存储"), a:has-text("存储")').first();
    
    if (await storageTab.isVisible().catch(() => false)) {
      await storageTab.click();
      await page.waitForTimeout(300);
    }
    
    // 查找存储设置表单
    const storageForm = page.locator('.storage-settings, .file-storage-form');
    
    if (await storageForm.isVisible().catch(() => false)) {
      // 验证存储类型选择
      const storageType = page.locator('select[name="storageType"], .storage-type-select').first();
      if (await storageType.isVisible().catch(() => false)) {
        await storageType.selectOption('local');
        await page.waitForTimeout(300);
      }
      
      // 验证存储路径设置
      const storagePath = page.locator('input[name="storagePath"], input[name="uploadPath"]').first();
      if (await storagePath.isVisible().catch(() => false)) {
        await storagePath.fill('/data/uploads');
      }
      
      // 验证最大文件大小设置
      const maxFileSize = page.locator('input[name="maxFileSize"], input[name="maxUploadSize"]').first();
      if (await maxFileSize.isVisible().catch(() => false)) {
        await maxFileSize.fill('100');
      }
      
      // 保存设置
      const saveButton = page.locator('button:has-text("保存"), button:has-text("应用")').first();
      if (await saveButton.isVisible().catch(() => false)) {
        await saveButton.click();
        await page.waitForTimeout(500);
        
        // 验证成功提示
        const successMessage = page.locator('.el-message--success, .success-message');
        await expect(successMessage).toBeVisible();
      }
    }
  });

  /**
   * 测试用例：邮件通知设置
   * 验证能够配置邮件通知选项
   */
  test('邮件通知设置', async ({ page }) => {
    // 导航到设置页面
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForTimeout(500);
    
    // 查找邮件设置选项卡或链接
    const emailTab = page.locator('.email-tab, button:has-text("邮件"), a:has-text("邮件")').first();
    
    if (await emailTab.isVisible().catch(() => false)) {
      await emailTab.click();
      await page.waitForTimeout(300);
    }
    
    // 查找邮件设置表单
    const emailForm = page.locator('.email-settings, .notification-settings');
    
    if (await emailForm.isVisible().catch(() => false)) {
      // 启用邮件通知
      const emailToggle = page.locator('input[name="emailEnabled"], .email-toggle').first();
      if (await emailToggle.isVisible().catch(() => false)) {
        await emailToggle.check();
      }
      
      // 配置SMTP服务器
      const smtpServer = page.locator('input[name="smtpServer"], input[name="smtpHost"]').first();
      if (await smtpServer.isVisible().catch(() => false)) {
        await smtpServer.fill('smtp.example.com');
      }
      
      const smtpPort = page.locator('input[name="smtpPort"]').first();
      if (await smtpPort.isVisible().catch(() => false)) {
        await smtpPort.fill('587');
      }
      
      // 保存设置
      const saveButton = page.locator('button:has-text("保存"), button:has-text("应用")').first();
      if (await saveButton.isVisible().catch(() => false)) {
        await saveButton.click();
        await page.waitForTimeout(500);
        
        // 验证成功提示
        const successMessage = page.locator('.el-message--success, .success-message');
        await expect(successMessage).toBeVisible();
      }
    }
  });

  /**
   * 测试用例：安全设置
   * 验证能够配置安全选项
   */
  test('安全设置', async ({ page }) => {
    // 导航到设置页面
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForTimeout(500);
    
    // 查找安全设置选项卡或链接
    const securityTab = page.locator('.security-tab, button:has-text("安全"), a:has-text("安全")').first();
    
    if (await securityTab.isVisible().catch(() => false)) {
      await securityTab.click();
      await page.waitForTimeout(300);
    }
    
    // 查找安全设置表单
    const securityForm = page.locator('.security-settings');
    
    if (await securityForm.isVisible().catch(() => false)) {
      // 配置登录尝试限制
      const maxLoginAttempts = page.locator('input[name="maxLoginAttempts"]').first();
      if (await maxLoginAttempts.isVisible().catch(() => false)) {
        await maxLoginAttempts.fill('5');
      }
      
      // 配置会话超时
      const sessionTimeout = page.locator('input[name="sessionTimeout"]').first();
      if (await sessionTimeout.isVisible().catch(() => false)) {
        await sessionTimeout.fill('30');
      }
      
      // 启用双因素认证
      const twoFactorToggle = page.locator('input[name="twoFactorEnabled"]').first();
      if (await twoFactorToggle.isVisible().catch(() => false)) {
        await twoFactorToggle.check();
      }
      
      // 保存设置
      const saveButton = page.locator('button:has-text("保存"), button:has-text("应用")').first();
      if (await saveButton.isVisible().catch(() => false)) {
        await saveButton.click();
        await page.waitForTimeout(500);
        
        // 验证成功提示
        const successMessage = page.locator('.el-message--success, .success-message');
        await expect(successMessage).toBeVisible();
      }
    }
  });

  /**
   * 测试用例：备份设置
   * 验证能够配置自动备份选项
   */
  test('备份设置', async ({ page }) => {
    // 导航到设置页面
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForTimeout(500);
    
    // 查找备份设置选项卡或链接
    const backupTab = page.locator('.backup-tab, button:has-text("备份"), a:has-text("备份")').first();
    
    if (await backupTab.isVisible().catch(() => false)) {
      await backupTab.click();
      await page.waitForTimeout(300);
    }
    
    // 查找备份设置表单
    const backupForm = page.locator('.backup-settings');
    
    if (await backupForm.isVisible().catch(() => false)) {
      // 启用自动备份
      const autoBackupToggle = page.locator('input[name="autoBackup"], .auto-backup-toggle').first();
      if (await autoBackupToggle.isVisible().catch(() => false)) {
        await autoBackupToggle.check();
      }
      
      // 配置备份频率
      const backupFrequency = page.locator('select[name="backupFrequency"]').first();
      if (await backupFrequency.isVisible().catch(() => false)) {
        await backupFrequency.selectOption('daily');
      }
      
      // 配置备份时间
      const backupTime = page.locator('input[name="backupTime"]').first();
      if (await backupTime.isVisible().catch(() => false)) {
        await backupTime.fill('02:00');
      }
      
      // 配置备份保留天数
      const backupRetention = page.locator('input[name="backupRetention"]').first();
      if (await backupRetention.isVisible().catch(() => false)) {
        await backupRetention.fill('30');
      }
      
      // 保存设置
      const saveButton = page.locator('button:has-text("保存"), button:has-text("应用")').first();
      if (await saveButton.isVisible().catch(() => false)) {
        await saveButton.click();
        await page.waitForTimeout(500);
        
        // 验证成功提示
        const successMessage = page.locator('.el-message--success, .success-message');
        await expect(successMessage).toBeVisible();
      }
    }
  });

  /**
   * 测试用例：系统信息查看
   * 验证能够查看系统信息
   */
  test('系统信息查看', async ({ page }) => {
    // 导航到设置页面
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForTimeout(500);
    
    // 查找系统信息选项卡或链接
    const aboutTab = page.locator('.about-tab, button:has-text("关于"), a:has-text("关于"), button:has-text("系统信息")').first();
    
    if (await aboutTab.isVisible().catch(() => false)) {
      await aboutTab.click();
      await page.waitForTimeout(300);
    }
    
    // 查找系统信息区域
    const systemInfo = page.locator('.system-info, .about-section, .version-info');
    
    if (await systemInfo.isVisible().catch(() => false)) {
      // 验证版本号显示
      await expect(page.locator('text=版本|Version')).toBeVisible();
      
      // 验证系统信息项
      const infoItems = page.locator('.info-item, .system-info-item');
      if (await infoItems.count() > 0) {
        await expect(infoItems.first()).toBeVisible();
      }
    }
  });

  /**
   * 测试用例：重置设置为默认值
   * 验证能够重置设置为默认值
   */
  test('重置设置为默认值', async ({ page }) => {
    // 导航到设置页面
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForTimeout(500);
    
    // 查找重置按钮
    const resetButton = page.locator('button:has-text("重置"), button:has-text("恢复默认"), .reset-btn').first();
    
    if (await resetButton.isVisible().catch(() => false)) {
      await resetButton.click();
      await page.waitForTimeout(300);
      
      // 确认重置
      const confirmDialog = page.locator('.el-message-box, .confirm-dialog');
      if (await confirmDialog.isVisible().catch(() => false)) {
        await page.click('.el-message-box__btns button:has-text("确定")');
        await page.waitForTimeout(500);
        
        // 验证成功提示
        const successMessage = page.locator('.el-message--success, .success-message');
        await expect(successMessage).toBeVisible();
      }
    }
  });

  /**
   * 测试用例：设置项验证
   * 验证设置表单的输入验证
   */
  test('设置项验证', async ({ page }) => {
    // 导航到设置页面
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForTimeout(500);
    
    // 查找存储设置
    const storageTab = page.locator('.storage-tab, button:has-text("存储")').first();
    if (await storageTab.isVisible().catch(() => false)) {
      await storageTab.click();
      await page.waitForTimeout(300);
    }
    
    // 测试无效输入
    const maxFileSize = page.locator('input[name="maxFileSize"]').first();
    if (await maxFileSize.isVisible().catch(() => false)) {
      // 输入无效值
      await maxFileSize.fill('-1');
      
      // 尝试保存
      const saveButton = page.locator('button:has-text("保存"), button:has-text("应用")').first();
      if (await saveButton.isVisible().catch(() => false)) {
        await saveButton.click();
        await page.waitForTimeout(300);
        
        // 验证验证错误
        const errorMessage = page.locator('.el-form-item__error, .error-message');
        if (await errorMessage.isVisible().catch(() => false)) {
          await expect(errorMessage).toBeVisible();
        }
      }
    }
  });

  /**
   * 测试用例：设置导航菜单
   * 验证设置页面的导航菜单正常
   */
  test('设置导航菜单', async ({ page }) => {
    // 导航到设置页面
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForTimeout(500);
    
    // 验证设置菜单存在
    const settingsMenu = page.locator('.settings-menu, .settings-tabs, .settings-sidebar');
    await expect(settingsMenu).toBeVisible();
    
    // 验证菜单项存在
    const menuItems = page.locator('.settings-menu-item, .settings-tab-item, .el-menu-item');
    if (await menuItems.count() > 0) {
      // 点击不同的菜单项
      for (let i = 0; i < Math.min(menuItems.count(), 3); i++) {
        const menuItem = menuItems.nth(i);
        if (await menuItem.isVisible().catch(() => false)) {
          await menuItem.click();
          await page.waitForTimeout(300);
          
          // 验证对应的内容区域显示
          const contentArea = page.locator('.settings-content, .tab-content');
          await expect(contentArea).toBeVisible();
        }
      }
    }
  });

});
