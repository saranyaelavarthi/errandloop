/* Run with a local server: node scripts/browser-test.cjs
 * Install playwright separately, then `npx playwright install chromium`.
 * Optional ERRANDLOOP_CHROMIUM_PACKAGE points to a compatible chromium package.
 */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {spawn}=require('node:child_process');
const base = process.env.ERRANDLOOP_URL || 'http://127.0.0.1:8000';
let stopServer=()=>{};

(async () => {
  if(process.env.ERRANDLOOP_START_SERVER==='1'){
    const server=spawn(process.env.ERRANDLOOP_PYTHON||'python',['-m','app.server','--demo','--port','8000']);
    stopServer=()=>server.kill();
    process.on('exit',()=>server.kill());
    await new Promise((resolve,reject)=>{
      server.stdout.once('data',resolve);
      server.once('error',reject);
      server.once('exit',code=>reject(new Error('Server exited: '+code)));
    });
  }
  let launch = {headless:true};
  if(process.env.ERRANDLOOP_CHROMIUM_PACKAGE){
    const imported = require(process.env.ERRANDLOOP_CHROMIUM_PACKAGE);
    const binary = imported.default || imported;
    launch = { ...launch, executablePath:await binary.executablePath(), args:binary.args };
  }
  const browser = await chromium.launch(launch);
  const page = await browser.newPage({viewport:{width:1440,height:1080},deviceScaleFactor:1});
  const errors = [];
  page.on('pageerror', e=>errors.push(e.message));
  page.on('console', m=>{if(m.type()==='error')errors.push(m.text());});
  const dialog=page.locator('#modal');
  const checkNoOverflow = async () => assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),'Horizontal overflow');
  const close=async()=>{if(await dialog.isVisible())await page.getByRole('button',{name:'Close dialog'}).click();};
  const reset=async()=>{
    await page.request.post(base+'/api/reset',{data:{},headers:{'Content-Type':'application/json'}});
    await page.goto(base);
    await page.evaluate(()=>localStorage.setItem('errandloop-actor','you'));
    await page.reload();
    await page.getByRole('heading',{name:'Going anyway?'}).waitFor();
  };
  fs.mkdirSync('docs',{recursive:true});
  await reset();
  await checkNoOverflow();
  await page.screenshot({path:'docs/desktop.png',fullPage:true});
  await page.getByRole('button',{name:'Review this circle'}).click();
  await dialog.getByRole('button',{name:'I’m in — propose this circle'}).click();
  await dialog.getByRole('button',{name:'Continue as Asha'}).click();
  await dialog.getByRole('button',{name:'Yes, I’m in'}).click();
  await dialog.getByRole('button',{name:'Continue as Ravi'}).click();
  await dialog.getByRole('button',{name:'Yes, I’m in'}).click();
  await dialog.getByText('Ready to go',{exact:true}).waitFor();
  assert.equal((await dialog.locator('.acceptance').innerText()).match(/\bYou\b/g).length,1);
  await page.screenshot({path:'docs/circle.png',fullPage:false});
  await dialog.getByRole('button',{name:'I’ve collected this'}).click();
  await dialog.getByRole('button',{name:'Continue as Asha'}).click();
  await dialog.getByRole('button',{name:'I’ve received this'}).click();
  await dialog.getByRole('button',{name:'I’ve collected this'}).click();
  await dialog.getByRole('button',{name:'Continue as Sana'}).click();
  await dialog.getByRole('button',{name:'I’ve received this'}).click();
  await dialog.getByRole('button',{name:'I’ve collected this'}).click();
  await dialog.getByRole('button',{name:'Continue as Ravi'}).click();
  await dialog.getByRole('button',{name:'I’ve received this'}).click();
  await dialog.getByText('Circle complete',{exact:true}).waitFor();
  await close();
  await page.reload();
  await page.getByRole('button',{name:/My circles/}).click();
  await page.getByText('Circle complete',{exact:true}).waitFor();
  console.log('PASS: three-person consent, collection, receipt, completion, persistence');

  await page.locator('#actor').selectOption('kabir');
  await page.getByRole('button',{name:'The board',exact:true}).click();
  await page.getByRole('button',{name:'I’m heading out'}).click();
  await dialog.getByLabel('I’m already going to').selectOption('library');
  await dialog.getByRole('button',{name:'Post my trip'}).click();
  await page.getByRole('button',{name:'I need a hand',exact:true}).click();
  await dialog.getByLabel('What needs collecting?').fill('My prepared notebook order');
  await dialog.getByRole('button',{name:'Post my request'}).click();
  await page.getByRole('button',{name:'Review this circle'}).waitFor();
  console.log('PASS: create trip + request; real matching after new input');

  await page.getByRole('tab',{name:/Need a hand/}).click();
  await page.getByLabel('Filter by destination').selectOption('grocery');
  await page.getByRole('heading',{name:'Around the courtyard'}).waitFor();
  await checkNoOverflow();
  await page.getByRole('button',{name:'Activity',exact:true}).click();
  const downloadPromise=page.waitForEvent('download');
  await page.getByRole('button',{name:'Download activity record'}).click();
  const download=await downloadPromise;
  assert.equal(download.suggestedFilename(),'errandloop-activity.json');
  console.log('PASS: destination filtering and activity export');

  await reset();
  await page.setViewportSize({width:390,height:844});
  await checkNoOverflow();
  await page.screenshot({path:'docs/mobile.png',fullPage:true});
  await page.getByRole('button',{name:'Review this circle'}).click();
  assert(await dialog.isVisible());
  await checkNoOverflow();
  await page.keyboard.press('Escape');
  assert(!(await dialog.isVisible()));
  await page.setViewportSize({width:768,height:1024});
  await checkNoOverflow();
  await page.setViewportSize({width:1280,height:900});
  await page.evaluate(()=>document.documentElement.style.fontSize='200%');
  await checkNoOverflow();
  await page.evaluate(()=>document.documentElement.style.fontSize='');
  console.log('PASS: phone, tablet, 200% text, dialog keyboard dismissal');
  assert.deepEqual(errors,[],'Browser console errors');
  await reset();
  await browser.close();
  stopServer();
  console.log('All browser checks passed. Demo reset for presentation.');
})().catch(e=>{console.error(e);process.exit(1);});
