// Renders the social media preview image and the app icons into public/ using headless
// Chromium and the bundled fonts, so they always match the app's neon look.
// Usage (dev server not needed):  node scripts/render_social.mjs
import { mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import puppeteer from 'puppeteer-core'

const root = fileURLToPath(new URL('..', import.meta.url))
const fonts = `file://${root}public/fonts`
const out = `${root}public`
mkdirSync(`${out}/icons`, { recursive: true })

const base = `
  @font-face { font-family: Pacifico; src: url(${fonts}/pacifico.ttf); }
  @font-face { font-family: Fredoka; src: url(${fonts}/fredoka.ttf); font-weight: 300 700; }
  * { margin: 0; box-sizing: border-box; }
  body { background: #09090b; color: #f4f4f5; font-family: Fredoka, sans-serif; overflow: hidden; }
  .neon { color: #fff; text-shadow: 0 0 6px #fff, 0 0 18px #ff3cac, 0 0 42px #ff3cac, 0 0 90px #ff3cac; }
  .grid { position: absolute; inset: 0; background-image: radial-gradient(#27272a 1px, transparent 1px); background-size: 28px 28px; opacity: .55; }
`

const ogImage = `<!doctype html><html><head><style>${base}
  .card { position: relative; width: 1200px; height: 630px; padding: 64px 72px; display: grid; grid-template-columns: 1fr 470px;
          gap: 48px; align-items: center; }
  .text { position: relative; display: flex; flex-direction: column; gap: 26px; }
  h1 { font-size: 66px; font-weight: 700; letter-spacing: -1px; line-height: 1.05; }
  h1 span { color: #f472b6; text-shadow: 0 0 22px rgba(255,60,172,.75); }
  p { font-size: 28px; color: #a1a1aa; line-height: 1.35; }
  .tags { display: flex; gap: 10px; flex-wrap: wrap; }
  .tag { font-size: 19px; padding: 7px 15px; border: 1px solid #3f3f46; border-radius: 999px; color: #d4d4d8; background: #18181b; }
  .plate { position: relative; height: 300px; border: 2px solid #3f3f46; border-radius: 22px; background: #111114;
           display: grid; place-items: center; box-shadow: 0 30px 80px rgba(0,0,0,.6); }
  .plate .neon { font-family: Pacifico; font-size: 118px; transform: rotate(-4deg) translateY(-14px); }
  .route { position: absolute; inset: 0; }
</style></head><body><div class="card">
  <div class="grid"></div>
  <div class="text">
    <h1><span>LED-Neon</span> Planer</h1>
    <p>Streifenlänge, Routing hinter der Platte und Druckvorlage für Leuchtschriften – direkt im Browser.</p>
    <div class="tags">
      <span class="tag">Biegeradius</span><span class="tag">Rückseiten-Routing</span><span class="tag">Zuschnittliste</span>
      <span class="tag">PDF 1:1 · A4 / A3</span><span class="tag">DE / EN</span>
    </div>
  </div>
  <div class="plate">
    <svg class="route" viewBox="0 0 470 300"><path d="M36 256 C 110 286, 170 236, 240 266 S 370 284, 434 248" fill="none" stroke="#f59e0b" stroke-width="3" stroke-dasharray="10 8" opacity=".75"/>
      <circle cx="36" cy="256" r="8" fill="none" stroke="#22c55e" stroke-width="3"/><circle cx="434" cy="248" r="8" fill="none" stroke="#f59e0b" stroke-width="3"/></svg>
    <div class="neon">Hallo</div>
  </div>
</div></body></html>`

const icon = (size) => `<!doctype html><html><head><style>${base}
  .icon { width: ${size}px; height: ${size}px; border-radius: ${size * 0.22}px; background: radial-gradient(circle at 50% 40%, #1f1023, #09090b 70%);
          display: grid; place-items: center; }
  .neon { font-family: Pacifico; font-size: ${size * 0.62}px; line-height: 1; transform: translateY(-${size * 0.04}px); }
</style></head><body style="background:transparent"><div class="icon"><div class="neon">N</div></div></body></html>`

const browser = await puppeteer.launch({
  executablePath: process.env.CHROMIUM || '/run/current-system/sw/bin/chromium',
  headless: true,
  args: ['--no-sandbox', '--allow-file-access-from-files'],
})

async function render(html, width, height, path, transparent = false) {
  const page = await browser.newPage()
  await page.setViewport({ width, height, deviceScaleFactor: 1 })
  await page.goto(`file://${root}index.html`) // file origin so the font URLs load
  await page.setContent(html, { waitUntil: 'load' })
  await page.evaluate(() => document.fonts.ready)
  await page.screenshot({ path, omitBackground: transparent, clip: { x: 0, y: 0, width, height } })
  await page.close()
  console.log('wrote', path.replace(root, ''))
}

await render(ogImage, 1200, 630, `${out}/og-image.png`)
for (const size of [180, 192, 512]) await render(icon(size), size, size, `${out}/icons/icon-${size}.png`, true)
await browser.close()
