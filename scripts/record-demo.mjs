import { chromium } from 'playwright';
import { mkdir, copyFile } from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, '..');
const DEMO_DIR = path.join(ROOT, 'docs', 'demo');
const PDF_PATH =
  process.env.DEMO_PDF ||
  'C:\\Users\\sasir\\Downloads\\reports\\Q1 FY27 Press Release.pdf';
const BASE_URL = process.env.APP_URL || 'http://localhost:3000';
const API_URL = process.env.API_URL || 'http://localhost:8001/api/v1';
const OUTPUT_NAME = process.env.DEMO_OUTPUT || 'knowledgepilot-demo-full.webm';

const email = `demo${Date.now()}@knowledgepilot.demo`;
const password = 'DemoPass123!';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let step = 0;
const log = (msg) => {
  step += 1;
  console.log(`${step}/${TOTAL_STEPS} ${msg}`);
};

const TOTAL_STEPS = 14;

await mkdir(DEMO_DIR, { recursive: true });

console.log('Starting full-feature demo recording...');
console.log(`PDF: ${PDF_PATH}`);
console.log(`App: ${BASE_URL}`);
console.log(`API: ${API_URL}`);
console.log(`User: ${email}`);

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  recordVideo: { dir: DEMO_DIR, size: { width: 1440, height: 900 } },
  locale: 'en-US',
});
const page = await context.newPage();

async function registerAndAuth() {
  const registerRes = await fetch(`${API_URL}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, full_name: 'Demo User' }),
  });
  if (!registerRes.ok) {
    const err = await registerRes.text();
    throw new Error(`Registration failed: ${registerRes.status} ${err}`);
  }
  const tokens = await registerRes.json();
  await context.addCookies([
    {
      name: 'access_token',
      value: tokens.access_token,
      domain: 'localhost',
      path: '/',
    },
    {
      name: 'refresh_token',
      value: tokens.refresh_token,
      domain: 'localhost',
      path: '/',
    },
  ]);
}

try {
  // 1. Landing page — hero + features
  log('Landing page (hero & features)');
  await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 60000 });
  await sleep(2500);
  await page.evaluate(() => window.scrollTo({ top: 600, behavior: 'smooth' }));
  await sleep(2500);
  await page.evaluate(() => {
    const el = document.querySelector('#features');
    el?.scrollIntoView({ behavior: 'smooth' });
  });
  await sleep(3000);
  await page.evaluate(() => {
    const el = document.querySelector('#how-it-works');
    el?.scrollIntoView({ behavior: 'smooth' });
  });
  await sleep(2500);

  // 2. Auth pages (UI)
  log('Login & Register pages');
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle' });
  await sleep(2000);
  await page.goto(`${BASE_URL}/register`, { waitUntil: 'networkidle' });
  await sleep(2000);

  // 3. Register via API and open dashboard
  log('Authenticate & Dashboard overview');
  await registerAndAuth();
  await page.goto(`${BASE_URL}/dashboard`, { waitUntil: 'networkidle' });
  await sleep(3000);
  await page.evaluate(() => window.scrollBy(0, 300));
  await sleep(1500);

  // 4. Documents — upload & processing
  log('Documents — upload PDF');
  await page.goto(`${BASE_URL}/dashboard/documents`, { waitUntil: 'networkidle' });
  await sleep(1500);

  const fileInput = page.locator('input[type="file"]');
  await fileInput.setInputFiles(PDF_PATH);
  await sleep(3000);

  console.log('   Waiting for document processing...');
  let processed = false;
  for (let i = 0; i < 60; i++) {
    await page.reload({ waitUntil: 'networkidle' });
    const completed = await page
      .getByText(/completed/i)
      .first()
      .isVisible()
      .catch(() => false);
    const failed = await page
      .getByText(/failed/i)
      .first()
      .isVisible()
      .catch(() => false);
    if (completed) {
      processed = true;
      console.log('   Document processed successfully');
      break;
    }
    if (failed) {
      console.log('   Document processing failed — continuing demo');
      break;
    }
    await sleep(5000);
  }
  if (!processed) console.log('   Processing still in progress or timed out');
  await sleep(2000);

  // 5. Semantic search
  log('Search — semantic');
  await page.goto(`${BASE_URL}/dashboard/search`, { waitUntil: 'networkidle' });
  await sleep(1500);
  const searchInput = page.getByPlaceholder(/Ask a question or search/i);
  await searchInput.fill('What are the Q1 FY27 financial highlights?');
  await searchInput.press('Enter');
  await sleep(8000);

  // 6. Hybrid search
  log('Search — hybrid mode');
  await page.getByRole('button', { name: 'Hybrid', exact: true }).click();
  await sleep(1000);
  await searchInput.fill('revenue growth operating margin');
  await searchInput.press('Enter');
  await sleep(8000);

  // 7. AI Chat
  log('AI Chat with citations');
  await page.goto(`${BASE_URL}/dashboard/chat`, { waitUntil: 'networkidle' });
  await sleep(1500);
  const chatInput = page.getByPlaceholder(/Ask a question about your documents/i);
  await chatInput.fill(
    'Summarize the key financial highlights from the Q1 FY27 press release.'
  );
  await page
    .locator('form')
    .filter({ has: chatInput })
    .locator('button[type="submit"]')
    .click();
  await sleep(22000);

  // Second chat message for session history
  await chatInput.fill('What was the revenue performance?');
  await page
    .locator('form')
    .filter({ has: chatInput })
    .locator('button[type="submit"]')
    .click();
  await sleep(15000);

  // 8. Analytics dashboard
  log('Analytics dashboard');
  await page.goto(`${BASE_URL}/dashboard/analytics`, { waitUntil: 'networkidle' });
  await page.waitForSelector('text=Daily Activity', { timeout: 15000 }).catch(() => {});
  await sleep(5000);
  await page.evaluate(() => window.scrollBy(0, 400));
  await sleep(3000);

  // 9. Knowledge Graph
  log('Knowledge Graph visualization');
  await page.goto(`${BASE_URL}/dashboard/knowledge-graph`, {
    waitUntil: 'networkidle',
  });
  await sleep(4000);
  // Click a document node if present
  const graphNode = page.locator('.react-flow__node').first();
  if (await graphNode.isVisible().catch(() => false)) {
    await graphNode.click();
    await sleep(2500);
  }
  await page.evaluate(() => {
    const canvas = document.querySelector('.react-flow__pane');
    canvas?.dispatchEvent(new WheelEvent('wheel', { deltaY: -200 }));
  });
  await sleep(1500);

  // 10. Sidebar navigation tour
  log('Sidebar navigation tour');
  const navHrefs = [
    '/dashboard',
    '/dashboard/chat',
    '/dashboard/documents',
    '/dashboard/search',
    '/dashboard/analytics',
    '/dashboard/knowledge-graph',
  ];
  for (const href of navHrefs) {
    await page.goto(`${BASE_URL}${href}`, { waitUntil: 'networkidle', timeout: 60000 });
    await sleep(1800);
  }

  // 11. Closing — landing page
  log('Closing — landing page');
  await page.goto(BASE_URL, { waitUntil: 'networkidle' });
  await sleep(2500);

  console.log('Full demo flow complete');
} catch (err) {
  console.error('Demo error:', err.message);
  await sleep(2000);
  try {
    await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 60000 });
    await sleep(2000);
  } catch {
    /* ignore */
  }
}

const video = page.video();
await page.close();
await context.close();
await browser.close();

if (video) {
  const tempPath = await video.path();
  const webmPath = path.join(DEMO_DIR, OUTPUT_NAME);
  await copyFile(tempPath, webmPath);
  // Also refresh the main demo file
  const mainPath = path.join(DEMO_DIR, 'knowledgepilot-demo.webm');
  await copyFile(tempPath, mainPath).catch(() => {});
  console.log(`Video saved: ${webmPath}`);
  console.log(`Also updated: ${mainPath}`);
}
