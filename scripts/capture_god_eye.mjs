/** Deterministic offline capture using upstream GEV's actual viewer factory.
 * npm ci --ignore-scripts in the pinned upstream checkout; install Puppeteer Chrome.
 * node scripts/capture_god_eye.mjs UPSTREAM SPEC_JSON OUTPUT_DIRECTORY
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
const [upArg,specArg,outArg]=process.argv.slice(2);
if(!outArg)throw Error('Usage: capture_god_eye.mjs UPSTREAM SPEC_JSON OUTPUT_DIRECTORY');
const upstream=path.resolve(upArg),out=path.resolve(outArg),spec=JSON.parse(await fs.readFile(specArg,'utf8'));
execFileSync('python',['-c','import json,sys; from tiktok_motion.geographic_director import validate_geography; validate_geography(json.load(open(sys.argv[1])))',path.resolve(specArg)]);
const upstreamCommit=execFileSync('git',['-C',upstream,'rev-parse','HEAD'],{encoding:'utf8'}).trim();
const approved='713285b554bbc99c8ae0261fe307beb3cbeb2adf';
if(upstreamCommit!==approved)throw Error('Upstream changed: review viewer and data licenses before capture');
// Currently the renderer supports one geodesic segment; never silently drop via points.
if(spec.route.length!==2)throw Error('Capture currently requires exactly two endpoints');
const moduleAt=name=>import(pathToFileURL(path.join(upstream,'node_modules',name)).href);
const {createServer}=await moduleAt('vite/dist/node/index.js');
const {default:cesium}=await moduleAt('vite-plugin-cesium/dist/index.mjs');
const {default:puppeteer}=await moduleAt('puppeteer/lib/puppeteer/puppeteer.js');
const entry=path.resolve('scripts/geo_capture/browser.mjs');
const html=`<html><meta charset="utf-8"><link rel="stylesheet" href="/cesium/Widgets/widgets.css"><style>html,body,#globe{margin:0;width:100%;height:100%;overflow:hidden;background:#020812}#credits{position:absolute;bottom:8px;left:18px;color:white}#hud{position:absolute;inset:0;pointer-events:none;color:#f0f8ff;font-family:Arial,sans-serif}#phase{position:absolute;top:42px;left:52px;font-size:18px;letter-spacing:4px;color:#61eed6}h1{position:absolute;top:65px;left:52px;font-size:44px;max-width:900px}#caption{position:absolute;bottom:72px;left:52px;font-size:28px;background:#061221cc;padding:16px 24px;border-left:4px solid #61eed6}#progress{position:absolute;bottom:49px;left:52px;height:3px;background:#61eed6;max-width:1176px}#label{position:absolute;right:40px;bottom:16px;font-size:12px;color:#b5c5d1}</style><div id="globe"></div><div id="hud"><div id="phase"></div><h1></h1><div id="caption"></div><div id="progress"></div><div id="label">ILLUSTRATIVE ROUTE · NATURAL EARTH / PUBLIC DOMAIN · ELLIPSOID TERRAIN</div></div><div id="credits"></div><script type="module" src="/@fs/${entry}"></script></html>`;
const server=await createServer({configFile:false,root:upstream,cacheDir:path.join(out,'.vite'),resolve:{alias:[{find:/^cesium$/,replacement:path.join(upstream,'node_modules/cesium/Source/Cesium.js')}]},plugins:[{name:'offline-capture-page',configureServer(s){s.middlewares.use('/capture.html',(_req,res)=>{res.setHeader('Content-Type','text/html');res.end(html)})}},cesium({cesiumBuildRootPath:path.join(upstream,'node_modules/cesium/Build')})],server:{host:'127.0.0.1',port:0,fs:{allow:[upstream,path.dirname(entry)]}}});

await fs.mkdir(out,{recursive:true});await server.listen();
let browser;
try{
 browser=await puppeteer.launch({headless:'shell',pipe:true,timeout:30000,args:['--no-sandbox','--no-zygote','--single-process','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const page=await browser.newPage();await page.setViewport({width:1280,height:720,deviceScaleFactor:1});
 page.on('response',async r=>{if(r.headers()['content-type']?.includes('text/html')&&!r.url().endsWith('capture.html'))console.log('UNEXPECTED HTML',r.url());});
 page.on('console',m=>console.log('CONSOLE',m.type(),m.text()));page.on('requestfailed',r=>console.log('REQUEST FAILED',r.url(),r.failure()));
 const errors=[];page.on('pageerror',e=>{errors.push(e.message);console.error('BROWSER ERROR',e.message)});
 await page.setRequestInterception(true);
 page.on('request',r=>new URL(r.url()).hostname==='127.0.0.1'||r.url().startsWith('data:')||r.url().startsWith('blob:')?r.continue():(console.error('BLOCKED',r.url()),r.abort()));
 await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/capture.html`);
 await page.waitForFunction('window.captureReady===true',{timeout:60000});
 await page.evaluate(s=>{document.querySelector('h1').textContent=s.title;window.setupCapture(s)},spec);
 await page.evaluate(()=>window.renderFrame(0));await page.screenshot({path:path.join(out,'warm.png')});console.log('WARM',await page.evaluate(()=>({tiles:window.captureViewer.scene.globe.tilesLoaded,url:window.location.href})));
 await page.evaluate(()=>{window.captureViewer.useDefaultRenderLoop=true;});
 // Warm all local basemap tiles along the camera path before any frame is admitted.
 for(const frame of [0,90,180,270,359]){
  let loaded=false;
  for(let attempt=0;attempt<200;attempt++){
   await page.evaluate(f=>window.renderFrame(f),Math.min(frame,spec.duration*30-1));
   // A readback flushes software-WebGL commands, including asynchronous tile uploads.
   await page.screenshot({type:'jpeg',quality:20});
   loaded=await page.evaluate(()=>window.captureViewer.scene.globe.tilesLoaded);
   if(loaded)break;
  }
  console.log('Warm pose',frame,'loaded',loaded);
  if(!loaded){console.log('TILE DEBUG',await page.evaluate(()=>{const g=window.captureViewer.scene.globe,s=g._surface;return {show:g.show,tiles:s._tilesToRender.length,high:s._tileLoadQueueHigh.length,medium:s._tileLoadQueueMedium.length,low:s._tileLoadQueueLow.length,roots:s._levelZeroTiles?.map(t=>({state:t.state,renderable:t.renderable,terrain:t.data?.terrainState,imagery:t.data?.imagery?.map(i=>i.loadingImagery?.state)}))}}));await page.screenshot({path:path.join(out,'failed.png')});throw Error('Local basemap failed to finish loading');}
 }

 await page.evaluate(()=>{window.captureViewer.useDefaultRenderLoop=false;window.captureViewer.resize();});
 const rendererHash=createHash('sha256').update(await fs.readFile(entry)).update(await fs.readFile(new URL(import.meta.url))).digest('hex');
 const fingerprint=createHash('sha256').update(JSON.stringify({spec,upstreamCommit,rendererHash,viewport:[1280,720],fps:30})).digest('hex');
 let prior;try{prior=JSON.parse(await fs.readFile(path.join(out,'capture.json'),'utf8'))}catch{}
 if(prior&&prior.fingerprint!==fingerprint)throw Error('Output belongs to another storyboard; use a new directory');
 await fs.writeFile(path.join(out,'capture.json'),JSON.stringify({fingerprint,rendererHash,upstreamCommit,spec,frames:spec.duration*30,basemap:'Cesium bundled NaturalEarthII; public domain',terrain:'WGS84 ellipsoid; no elevation dataset',externalRequestsAllowed:false},null,2));
 for(let f=0;f<spec.duration*30;f++){
  const dest=path.join(out,`frame_${String(f).padStart(5,'0')}.png`);
  try{const bytes=await fs.readFile(dest);if(bytes.length>100&&bytes.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10])))continue}catch{}
  await page.evaluate(frame=>window.renderFrame(frame),f);
  if(errors.length)throw Error(errors.join('\n'));
  const tmp=dest+'.tmp';await page.screenshot({path:tmp,type:'png',optimizeForSpeed:true});await fs.rename(tmp,dest);
  if(f%30===0)console.log(`Captured ${f}/${spec.duration*30}`);
 }
 execFileSync('ffmpeg',['-y','-loglevel','error','-framerate','30','-i',path.join(out,'frame_%05d.png'),'-frames:v',String(spec.duration*30),'-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',path.join(out,'capture.mp4')]);
 console.log(path.join(out,'capture.mp4'));
}finally{if(browser)await browser.close();await server.close();}
