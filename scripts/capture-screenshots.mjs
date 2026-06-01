import { chromium } from 'playwright';
import { mkdir } from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const outDir = path.join(__dirname, '..', 'docs', 'screenshots');
const baseUrl = process.env.APP_URL || 'http://localhost:3001';

const pages = [
  { name: 'landing', path: '/', wait: 2000 },
  { name: 'login', path: '/login', wait: 1500 },
  { name: 'register', path: '/register', wait: 1500 },
];

await mkdir(outDir, { recursive: true });

const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 2,
});
const page = await context.newPage();

for (const entry of pages) {
  await page.goto(`${baseUrl}${entry.path}`, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(entry.wait);
  await page.screenshot({
    path: path.join(outDir, `${entry.name}.png`),
    fullPage: false,
  });
  console.log(`Captured ${entry.name}.png`);
}

await browser.close();
console.log('Done');
