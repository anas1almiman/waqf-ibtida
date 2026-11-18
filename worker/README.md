# خادم «اسأل المكتبة» (Cloudflare Worker)
1. حساب Cloudflare مجاني، ثم: `npm i -g wrangler && wrangler login`
2. من هذا المجلد: `wrangler deploy`
3. `wrangler secret put ANTHROPIC_API_KEY` (الصق مفتاحك)
4. انسخ رابط الـWorker (مثل https://waqf-ai.<اسمك>.workers.dev) وأعطه لـClaude ليضعه في التطبيق.
اختياري: `MODEL` و`XMODEL` و`ALLOW` متغيّرات بيئة لتغيير النموذج أو النطاق المسموح.
