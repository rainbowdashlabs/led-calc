// End-to-end test in headless Chromium:
// loads the app, waits for the plan, checks all views, the path editor, the share code
// and the PDF download. Usage: node scripts/e2e.mjs <url> <out-dir> [settings-json]
import { mkdirSync, readdirSync, statSync } from 'node:fs'
import puppeteer from 'puppeteer-core'

const [url = 'http://localhost:5173/', out = 'e2e-out', settings] = process.argv.slice(2)
mkdirSync(out, { recursive: true })
const browser = await puppeteer.launch({
  executablePath: process.env.CHROMIUM || '/run/current-system/sw/bin/chromium',
  headless: true,
  args: ['--no-sandbox', '--disable-gpu'],
})
const page = await browser.newPage()
await page.setViewport({ width: 1500, height: 1100 })
const errors = []
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()) })
page.on('pageerror', (e) => errors.push('pageerror: ' + e.message))
await page.evaluateOnNewDocument(() => localStorage.setItem('led-neon-planer:lang', 'de'))
if (settings) await page.evaluateOnNewDocument((s) => localStorage.setItem('led-neon-planer:v1', s), settings)

const step = (name) => console.log(`✓ ${name}`)
const clickText = (text) => page.evaluate((t) => {
  const b = [...document.querySelectorAll('button')].find((x) => x.textContent.trim().startsWith(t))
  if (!b) throw new Error('button not found: ' + t)
  b.click()
}, text)

const t0 = Date.now()
await page.goto(url, { waitUntil: 'domcontentloaded' })
try {
  await page.waitForFunction(() => document.body.innerText.includes('zu kaufen'), { timeout: 240000 })
} catch {
  await page.screenshot({ path: `${out}/timeout.png` })
  console.log('TIMEOUT', errors.join('\n'))
  process.exit(1)
}
step(`plan ready after ${((Date.now() - t0) / 1000).toFixed(1)} s`)
await new Promise((r) => setTimeout(r, 800))
await page.screenshot({ path: `${out}/front.png` })

for (const [label, file] of [['Rückseite', 'back'], ['Ergebnis', 'result']]) {
  await clickText(label)
  await new Promise((r) => setTimeout(r, 400))
  await page.screenshot({ path: `${out}/${file}.png` })
  step(`view ${label}`)
}
await clickText('Vorderseite')

// path editor: drag the first handle and expect a recomputation marked as manual
await clickText('Pfade bearbeiten')
await new Promise((r) => setTimeout(r, 300))
const handle = await page.$('svg circle.cursor-move')
const box = await handle.boundingBox()
await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2)
await page.mouse.down()
await page.mouse.move(box.x + 40, box.y + 25, { steps: 8 })
await page.mouse.up()
await page.waitForFunction(() => document.body.innerText.includes('manuell bearbeitet'), { timeout: 60000 })
await page.screenshot({ path: `${out}/edit.png` })
step('manual edit recomputed')

// repeated drags must move points, never create extra curves
const count = () => page.$$eval('svg .cursor-move', (c) => c.length)
const before = await count()
for (let k = 0; k < 2; k++) {
  const handles = await page.$$('svg .cursor-move')
  const b = await handles[3 + k * 5].boundingBox()
  await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2)
  await page.mouse.down()
  await page.mouse.move(b.x + 20, b.y + 12, { steps: 6 })
  await page.mouse.up()
  await new Promise((r) => setTimeout(r, 2000))
}
if ((await count()) !== before) throw new Error('dragging changed the number of points')
step('repeated drags keep the points')

// hovering a point opens the point menu (icons with tooltips)
const hb = await (await page.$$('svg .cursor-move'))[2].boundingBox()
await page.mouse.move(hb.x + hb.width / 2, hb.y + hb.height / 2)
await page.waitForSelector('[role=menu] [aria-label="Rund (Spline)"]', { timeout: 5000 })
await page.screenshot({ path: `${out}/menu.png` })
step('point menu on hover')
await page.mouse.move(5, 5)
await page.waitForFunction(() => !document.querySelector('[role=menu]'), { timeout: 5000 })

// undo / redo of moving a point
// centre of every point marker (circles and squares; the marker size depends on the selection)
const handlePos = () => page.$$eval('svg .cursor-move', (c) => c.map((e) => {
  const b = e.getBBox()
  return [b.x + b.width / 2, b.y + b.height / 2]
}))
/** Same points within a small tolerance (marker sizes change with the selection). */
const samePositions = (a, b) => a.length === b.length && a.every(([x, y], i) => Math.hypot(x - b[i][0], y - b[i][1]) < 0.2)
const original = await handlePos()
const mb = await (await page.$$('svg .cursor-move'))[20].boundingBox()
await page.mouse.move(mb.x + mb.width / 2, mb.y + mb.height / 2)
await page.mouse.down()
await page.mouse.move(mb.x + 30, mb.y + 30, { steps: 6 })
await page.mouse.up()
await new Promise((r) => setTimeout(r, 500))
const moved = await handlePos()
if (samePositions(moved, original)) throw new Error('point did not move')
await page.keyboard.down('Control')
await page.keyboard.press('z')
await page.keyboard.up('Control')
await new Promise((r) => setTimeout(r, 300))
if (!samePositions(await handlePos(), original)) throw new Error('undo did not restore the point')
await page.keyboard.down('Control')
await page.keyboard.down('Shift')
await page.keyboard.press('z')
await page.keyboard.up('Shift')
await page.keyboard.up('Control')
await new Promise((r) => setTimeout(r, 300))
if (!samePositions(await handlePos(), moved)) throw new Error('redo did not move the point again')
step('undo / redo of a moved point')

// undo of deleting a piece (via the undo button)
const pieceCount = () => page.$$eval('svg g[filter] polyline, svg g[filter] polygon', (c) => c.length)
const piecesBefore = await pieceCount()
// clicking one of its points selects a piece
const sel = await (await page.$$('svg .cursor-move'))[0].boundingBox()
await page.mouse.click(sel.x + sel.width / 2, sel.y + sel.height / 2)
await page.mouse.move(5, 5)
await page.waitForFunction(() => !document.querySelector('[role=menu]'), { timeout: 5000 })
await page.keyboard.press('Delete')
await new Promise((r) => setTimeout(r, 300))
if ((await pieceCount()) !== piecesBefore - 1) throw new Error('piece was not deleted')
await page.click('[aria-label="Rückgängig (Strg+Z)"]')
await new Promise((r) => setTimeout(r, 300))
if ((await pieceCount()) !== piecesBefore) throw new Error('undo did not restore the piece')
step('undo of a deleted piece')

// draw two new pieces in the empty margin of the plate, then join them by dragging an end
const plate = await (await page.$('svg rect')).boundingBox()
const at = (fx, fy) => [plate.x + plate.width * fx, plate.y + plate.height * fy]
const clickAt = async ([x, y]) => { await page.mouse.click(x, y); await new Promise((r) => setTimeout(r, 120)) }
const drawPiece = async (points) => {
  await page.evaluate(() => [...document.querySelectorAll('button')].find((b) => b.textContent.includes('Neues Stück zeichnen')).click())
  for (const pt of points) await clickAt(pt)
  await page.keyboard.press('Enter')
  await new Promise((r) => setTimeout(r, 300))
}
const beforeDraw = await pieceCount()
await drawPiece([at(0.25, 0.93), at(0.35, 0.9), at(0.45, 0.93)])
await drawPiece([at(0.55, 0.93), at(0.65, 0.9)])
if ((await pieceCount()) !== beforeDraw + 2) throw new Error('drawing did not add two pieces')
step('draw new pieces')

const handles = await page.$$('svg .cursor-move')
const endOfFirst = await handles[handles.length - 3].boundingBox()   // last point of the first new piece
const startOfSecond = await handles[handles.length - 2].boundingBox() // first point of the second new piece
await page.mouse.move(startOfSecond.x + startOfSecond.width / 2, startOfSecond.y + startOfSecond.height / 2)
await page.mouse.down()
await page.mouse.move(endOfFirst.x + endOfFirst.width / 2, endOfFirst.y + endOfFirst.height / 2, { steps: 10 })
await page.mouse.up()
await new Promise((r) => setTimeout(r, 300))
if ((await pieceCount()) !== beforeDraw + 1) throw new Error('dragging an end onto another end did not join the pieces')
await page.keyboard.down('Control')
await page.keyboard.press('z')
await page.keyboard.up('Control')
await new Promise((r) => setTimeout(r, 300))
if ((await pieceCount()) !== beforeDraw + 2) throw new Error('undo did not split the joined pieces again')
step('join pieces by dragging an end, undo')

// cut a piece at an inner point via the point menu
const firstNew = (await page.$$('svg .cursor-move')).at(-4) // middle point of the first drawn piece
const fb = await firstNew.boundingBox()
await page.mouse.move(fb.x + fb.width / 2, fb.y + fb.height / 2)
await page.waitForSelector('[role=menu] [aria-label^="Hier schneiden"]', { timeout: 5000 })
await page.click('[role=menu] [aria-label^="Hier schneiden"]')
await new Promise((r) => setTimeout(r, 300))
if ((await pieceCount()) !== beforeDraw + 3) throw new Error('cutting did not split the piece')
step('cut a piece at a point')
await page.screenshot({ path: `${out}/draw.png` })
await clickText('Bearbeitung beenden')

// share code round trip
await clickText('Code')
await page.waitForSelector('textarea[readonly]')
const code = await page.$eval('textarea[readonly]', (t) => t.value)
if (!code.startsWith('NP1.')) throw new Error('bad share code')
await page.type('textarea[placeholder="NP1.…"]', code)
await clickText('Laden')
await page.waitForFunction(() => document.body.innerText.includes('Layout geladen'), { timeout: 30000 })
step(`share code round trip (${code.length} chars)`)

// PDF download
const cdp = await page.createCDPSession()
await cdp.send('Browser.setDownloadBehavior', { behavior: 'allow', downloadPath: out })
await page.waitForFunction(() => document.body.innerText.includes('zu kaufen'))
await clickText('PDF herunterladen')
const t1 = Date.now()
let pdf = null
while (Date.now() - t1 < 120000 && !pdf) {
  await new Promise((r) => setTimeout(r, 500))
  pdf = readdirSync(out).find((f) => f.endsWith('.pdf'))
}
if (!pdf) throw new Error('no pdf downloaded')
step(`pdf ${pdf} (${Math.round(statSync(`${out}/${pdf}`).size / 1024)} KiB) after ${((Date.now() - t1) / 1000).toFixed(1)} s`)

// DXF export for CNC milling
await page.evaluate(() => [...document.querySelectorAll('button')].find((x) => x.textContent.includes('DXF für CNC')).click())
const t2 = Date.now()
let dxf = null
while (Date.now() - t2 < 60000 && !dxf) {
  await new Promise((r) => setTimeout(r, 300))
  dxf = readdirSync(out).find((f) => f.endsWith('.dxf'))
}
if (!dxf) throw new Error('no dxf downloaded')
step(`dxf ${dxf} (${Math.round(statSync(`${out}/${dxf}`).size / 1024)} KiB)`)

// phone layout: tab bar switches areas, nothing scrolls sideways
await page.setViewport({ width: 390, height: 844, isMobile: true, hasTouch: true })
await page.waitForSelector('nav[aria-label] button', { visible: true, timeout: 10000 })
await page.evaluate(() => [...document.querySelectorAll('nav[aria-label] button')].find((b) => b.textContent.includes('Ergebnis')).click())
await page.waitForFunction(() => document.body.innerText.includes('Zuschnittliste'), { timeout: 10000 })
const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
if (overflow > 0) throw new Error(`page scrolls sideways on a phone by ${overflow}px`)
await page.screenshot({ path: `${out}/phone-results.png` })
step('phone layout with tab bar')

console.log(errors.length ? 'console errors:\n' + errors.join('\n') : 'no console errors')
await browser.close()
