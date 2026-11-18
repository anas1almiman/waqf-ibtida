// Cloudflare Worker: وسيط «اسأل المكتبة». المفتاح يبقى سرًّا هنا ولا يصل للتطبيق.
const SITE='https://anas1almiman.github.io/waqf-ibtida/';
const SYS=`أنت «مساعد المكتبة» في تطبيق «وقف وابتداء». تجيب عن سؤال المستخدم اعتمادًا حصريًّا على المصادر المرفقة: صور صفحات من كتب المكتبة ونصوصها المستخرجة آليًّا (قد يكون فيها أخطاء قراءة، فاعتمد الصورة إن وُجدت).
القواعد:
- لا تستعمل أي معلومة من خارج المصادر المرفقة. إن لم تجد الجواب فيها فقل بوضوح: «لم أجد هذا في كتب المكتبة»، واقترح صياغة أخرى للسؤال.
- كل معلومة تنسبها لمصدر ضع بعدها رقمه هكذا [١] أو [٢]، بحسب ترقيم المصادر المعطاة. لا تذكر رقمًا لمصدر لم تستفد منه.
- انقل كلام العلماء بدقة، ومثّل بنصوص قصيرة عند الحاجة، وانسب كل قول لقائله وكتابه.
- إن اختلفت الكتب فاعرض الأقوال وبيّن من قال بها.
- أجب بالعربية الفصحى الواضحة، بإيجاز منظّم: خلاصة في سطرين ثم التفصيل بنقاط قصيرة عند الحاجة.
- لا تُصدر فتوى شخصية. أنت تلخّص ما في الكتب وتنسبه إلى أصحابها.`;
const XSYS='حوّل سؤال المستخدم إلى كلمات مفتاحية عربية للبحث في كتب (الوقف والابتداء، التوحيد، التفسير...). أعد سطرًا واحدًا فقط: من ٦ إلى ١٢ كلمة أو عبارة قصيرة، تتضمن المرادفات والمصطلحات الشرعية المحتملة، بلا شرح.';
function cors(env,req){const o=req.headers.get('Origin')||'';const ok=(env.ALLOW||SITE.replace(/\/waqf-ibtida\/$/,'')).split(',');const a=ok.includes(o)||/^http:\/\/localhost(:\d+)?$/.test(o)?o:ok[0];return{'Access-Control-Allow-Origin':a,'Access-Control-Allow-Methods':'POST,OPTIONS','Access-Control-Allow-Headers':'Content-Type','Vary':'Origin'}}
const b64=buf=>{let s='';const a=new Uint8Array(buf);for(let i=0;i<a.length;i+=0x8000)s+=String.fromCharCode.apply(null,a.subarray(i,i+0x8000));return btoa(s)};
async function claude(env,body){return fetch('https://api.anthropic.com/v1/messages',{method:'POST',headers:{'x-api-key':env.ANTHROPIC_API_KEY,'anthropic-version':'2023-06-01','content-type':'application/json'},body:JSON.stringify(body)})}
export default{async fetch(req,env){
  const H=cors(env,req);
  if(req.method==='OPTIONS')return new Response(null,{status:204,headers:H});
  if(req.method!=='POST')return new Response('ok',{headers:H});
  if(env.RL){const ip=req.headers.get('CF-Connecting-IP')||'x';const r=await env.RL.limit({key:ip});if(!r.success)return new Response('كثرة طلبات، حاول بعد دقيقة.',{status:429,headers:H})}
  const path=new URL(req.url).pathname;let j;try{j=await req.json()}catch(e){return new Response('bad',{status:400,headers:H})}
  const q=String(j.q||'').slice(0,600);if(!q)return new Response('bad',{status:400,headers:H});
  const hist=(Array.isArray(j.h)?j.h:[]).slice(-6).map(m=>({role:m.r==='a'?'assistant':'user',content:String(m.c||'').slice(0,1500)}));
  if(path.endsWith('/expand')){
    const r=await claude(env,{model:env.XMODEL||'claude-haiku-5-5',max_tokens:120,system:XSYS,messages:[...hist.slice(-2),{role:'user',content:q}]});
    const d=await r.json().catch(()=>({}));const t=(d.content&&d.content[0]&&d.content[0].text)||'';
    return new Response(JSON.stringify({kw:t.slice(0,300)}),{headers:{...H,'Content-Type':'application/json'}});
  }
  const ctx=(Array.isArray(j.c)?j.c:[]).slice(0,10);let used=0;
  const parts=[];
  const imgs=(Array.isArray(j.i)?j.i:[]).slice(0,4);
  for(const u of imgs){const m=/^books\/[a-z0-9_]+\/p\d+\.(webp|png)$/.exec(String(u.u||''));if(!m)continue;
    try{const r=await fetch(SITE+u.u);if(!r.ok)continue;const buf=await r.arrayBuffer();if(buf.byteLength>4e6)continue;
      parts.push({type:'text',text:'صورة المصدر ['+u.n+']:'});parts.push({type:'image',source:{type:'base64',media_type:m[1]==='png'?'image/png':'image/webp',data:b64(buf)}})}catch(e){}}
  let txt='';for(const c of ctx){const x=String(c.x||'').slice(0,1800);if(used+x.length>20000)break;used+=x.length;txt+='\n['+c.n+'] '+String(c.t||'').slice(0,120)+' — صفحة '+String(c.p||'')+':\n'+x+'\n'}
  parts.push({type:'text',text:'المصادر المنقولة نصًّا (قراءة آلية):\n'+txt+'\n\nالسؤال: '+q});
  const r=await claude(env,{model:env.MODEL||'claude-sonnet-5-5',max_tokens:1600,stream:true,system:SYS,messages:[...hist,{role:'user',content:parts}]});
  if(!r.ok)return new Response('تعذّر الاتصال بالنموذج ('+r.status+')',{status:502,headers:H});
  const dec=new TextDecoder(),enc=new TextEncoder();let buf='';
  const ts=new TransformStream({transform(ch,c){buf+=dec.decode(ch,{stream:true});let i;while((i=buf.indexOf('\n'))>=0){const l=buf.slice(0,i).trim();buf=buf.slice(i+1);if(l.startsWith('data:')){try{const e=JSON.parse(l.slice(5));if(e.type==='content_block_delta'&&e.delta&&e.delta.text)c.enqueue(enc.encode(e.delta.text))}catch(x){}}}}});
  return new Response(r.body.pipeThrough(ts),{headers:{...H,'Content-Type':'text/plain; charset=utf-8','Cache-Control':'no-store'}});
}}
