import * as C from 'cesium';
import {createApplicationViewer} from '/src/app/viewer.js';

C.Ion.defaultAccessToken='';
C.buildModuleUrl.setBaseUrl('/cesium/');
const viewer=createApplicationViewer({container:document.getElementById('globe'),creditContainer:document.getElementById('credits')});
viewer.useDefaultRenderLoop=false;
viewer.scene.skyBox.show=false;
viewer.scene.sun.show=false;
viewer.scene.skyAtmosphere.atmosphereLightIntensity=10;
viewer.scene.skyAtmosphere.brightnessShift=-.2;
viewer.scene.globe.show=true;
viewer.scene.globe.enableLighting=false;
viewer.scene.globe.baseColor=C.Color.fromCssColorString('#12354b');
viewer.scene.backgroundColor=C.Color.fromCssColorString('#020812');
// Flat terrain needs no worker pool. Use Cesium's own synchronous tessellator
// in this pinned, CPU-only capture adapter; fail explicitly if its API changes.
const terrain=new C.EllipsoidTerrainProvider();
const requestGeometry=terrain.requestTileGeometry.bind(terrain);
terrain.requestTileGeometry=(...args)=>Promise.resolve(requestGeometry(...args)).then(data=>{
 if(typeof data._createMeshSync!=='function')throw Error('Pinned Cesium synchronous terrain API changed');
 data.createMesh=options=>Promise.resolve(data._createMeshSync(options));
 return data;
});
viewer.terrainProvider=terrain;
const basemap=viewer.imageryLayers.addImageryProvider(await C.TileMapServiceImageryProvider.fromUrl(C.buildModuleUrl('Assets/Textures/NaturalEarthII')));
basemap.brightness=.8;basemap.contrast=1.15;
viewer.scene.screenSpaceCameraController.enableInputs=false;
const smooth=t=>{t=Math.max(0,Math.min(1,t));return t*t*(3-2*t)};
window.setupCapture=spec=>{
 const route=spec.route, a=route[0], b=route.at(-1);
 const geodesic=new C.EllipsoidGeodesic(C.Cartographic.fromDegrees(a.lon,a.lat),C.Cartographic.fromDegrees(b.lon,b.lat));
 const routeLines=viewer.scene.primitives.add(new C.PolylineCollection());
 const path=routeLines.add({positions:[C.Cartesian3.fromDegrees(a.lon,a.lat,60000),C.Cartesian3.fromDegrees(b.lon,b.lat,60000)],width:6,material:C.Material.fromType('Color',{color:C.Color.fromCssColorString('#5cffe1')})});
 const marker=viewer.entities.add({position:C.Cartesian3.fromDegrees(a.lon,a.lat,10000),point:{pixelSize:14,color:C.Color.WHITE,outlineColor:C.Color.fromCssColorString('#5cffe1'),outlineWidth:5,disableDepthTestDistance:Number.POSITIVE_INFINITY}});
 for(const p of [a,b])viewer.entities.add({position:C.Cartesian3.fromDegrees(p.lon,p.lat,10000),point:{pixelSize:9,color:C.Color.fromCssColorString('#ffcc82')},label:{text:p.label,font:'bold 22px sans-serif',fillColor:C.Color.WHITE,showBackground:true,backgroundColor:C.Color.fromCssColorString('#071420dd'),pixelOffset:new C.Cartesian2(0,-30),disableDepthTestDistance:Number.POSITIVE_INFINITY}});
 const trace=spec.cues[1].at,arrival=spec.cues[2].at;
 window.renderFrame=async frame=>{
  const t=frame/30, zoom=smooth(t/trace), progress=smooth((t-trace)/(arrival-trace));
  const mid=geodesic.interpolateUsingFraction(.5);
  const finish=smooth((t-arrival)/(spec.duration-arrival));
  viewer.camera.setView({destination:C.Cartesian3.fromDegrees(-55+(C.Math.toDegrees(mid.longitude)+55)*zoom+(b.lon-C.Math.toDegrees(mid.longitude))*finish,20+(C.Math.toDegrees(mid.latitude)-20)*zoom+(b.lat-C.Math.toDegrees(mid.latitude))*finish,22000000*(1-zoom)+8500000*zoom-4500000*finish),orientation:{heading:0,pitch:-Math.PI/2,roll:0}});
  const positions=[];
  for(let i=0;i<=100;i++){const p=geodesic.interpolateUsingFraction(progress*i/100);positions.push(C.Cartesian3.fromRadians(p.longitude,p.latitude,60000));}
  path.positions=positions;path.show=t>=trace;
  const p=geodesic.interpolateUsingFraction(progress); marker.position=C.Cartesian3.fromRadians(p.longitude,p.latitude,60000);
  document.getElementById('phase').textContent=t<trace?'01 / LOCATE THE DEPARTURE':t<arrival?'02 / TRACE THE CROSSING':'03 / ARRIVE AT THE DESTINATION';
  const active=[...spec.cues].reverse().find(c=>t>=c.at);document.getElementById('caption').textContent=active?.phrase||'';
  document.getElementById('progress').style.width=(100*progress)+'%';
  viewer.resize();viewer.render();
  await new Promise(r=>requestAnimationFrame(r));viewer.render();
 };
 window.captureViewer=viewer;
};
window.captureReady=true;
