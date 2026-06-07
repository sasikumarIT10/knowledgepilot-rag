import { chromium } from 'playwright';

const BASE = process.env.APP_URL || 'http://localhost:3000';
const pages = [
  '/',
  '/login',
  '/register',
  '/dashboard',
  '/dashboard/documents',
  '/dashboard/search',
  '/dashboard/chat',
  '/dashboard/analytics',
  '/dashboard/knowledge-graph',
];

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
let failed = 0;

for (const path of pages) {
  try {
    const response = await page.goto(`${BASE}${path}`, {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    });
    const status = response?.status() ?? 0;
    const ok = status >= 200 && status < 400;
    console.log(`${ok ? 'PASS' : 'FAIL'} ${path} (${status})`);
    if (!ok) failed++;
  } catch (err) {
    console.log(`FAIL ${path} (${err.message})`);
    failed++;
  }
}

await browser.close();
process.exit(failed ? 1 : 0);
