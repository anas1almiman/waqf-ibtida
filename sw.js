const V='maqati-v27',DATA='maqati-data-1';
const CORE=['./','index.html','manifest.webmanifest','icon-192.png','icon-512.png','icon-180.png','apple-touch-icon.png'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(V).then(c=>c.addAll(CORE)).then(()=>caches.open(DATA)).then(c=>c.match('gharib.json?v=1').then(m=>m||c.add('gharib.json?v=1')).catch(()=>{})).then(()=>self.skipWaiting()))});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==V&&k!==DATA).map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
self.addEventListener('fetch',e=>{
  const u=new URL(e.request.url);
  if(e.request.method!=='GET')return;
  if(u.pathname.indexOf('/audio/')>=0||e.request.headers.has('range'))return;
  if(u.origin===location.origin&&(e.request.mode==='navigate'||u.pathname.endsWith('/index.html'))){
    e.respondWith(fetch(e.request).then(r=>{const c=r.clone();caches.open(V).then(x=>x.put('index.html',c));return r}).catch(()=>caches.match('index.html')));return;
  }
  if(u.origin===location.origin||u.host.endsWith('fonts.gstatic.com')||u.host.endsWith('fonts.googleapis.com')){
    const data=u.origin===location.origin&&(u.pathname.indexOf('/books/')>=0||u.pathname.indexOf('/timing/')>=0||u.pathname.endsWith('/gharib.json'));
    e.respondWith(caches.match(e.request).then(m=>m||fetch(e.request).then(r=>{if(r.ok){const c=r.clone();caches.open(data?DATA:V).then(x=>x.put(e.request,c))}return r})));
  }
});
