import { test } from 'node:test';
import assert from 'node:assert/strict';
import { seoCommand } from '../src/index.js';

test('no key: no network or fake SEO results', async () => {
  const old = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async () => { calls++; throw Error('should not call'); };
  try {
    const text = await seoCommand({}, 'es ballenas jorobadas');
    assert.match(text, /YOUTUBE_API_KEY/);
    assert.equal(calls, 0);
  } finally { globalThis.fetch = old; }
});

test('official bounded API search includes region and returns real observed stats', async () => {
  const old = globalThis.fetch;
  const called = [];
  const ID = 'A1b2C3d4E5F';
  const CH = 'UC' + 'a'.repeat(22);
  globalThis.fetch = async (url) => {
    const u = new URL(String(url));
    called.push(u);
    if (u.pathname.endsWith('/search')) return Response.json({ items: [{ id: { videoId: ID } }] });
    if (u.pathname.endsWith('/videos')) return Response.json({ items: [{
      id: ID, snippet: { title: '<b>Practical SEO</b>', channelId: CH,
        tags: ['cybersecurity', '<bad>'] },
      statistics: { viewCount: '1200' },
    }] });
    if (u.pathname.endsWith('/channels')) return Response.json({ items: [{
      id: CH, statistics: { subscriberCount: '55' },
    }] });
    throw Error('Unexpected endpoint');
  };
  try {
    const response = await seoCommand({ YOUTUBE_API_KEY: 'SECRET_VALUE' }, 'en cybersecurity');
    assert.equal(called.length, 3);
    assert.equal(called[0].searchParams.get('regionCode'), 'US');
    assert.equal(called[0].searchParams.get('relevanceLanguage'), 'en');
    assert.match(response, /Views: 1200/);
    assert.match(response, /Channel subs: 55/);
    assert.doesNotMatch(response, /SECRET_VALUE|<bad>|<b>Practical SEO<\/b>/);
    assert.match(response, /&lt;b&gt;Practical SEO&lt;\/b&gt;/);
    assert.match(response, /apwobasyon/);
  } finally { globalThis.fetch = old; }
});

test('API failure never makes up stats or echoes secrets', async () => {
  const old = globalThis.fetch;
  globalThis.fetch = async () => new Response('secret-key', { status: 403 });
  try {
    const response = await seoCommand({ YOUTUBE_API_KEY: 'secret-key' }, 'es jaguar');
    assert.match(response, /pa disponib/);
    assert.doesNotMatch(response, /secret-key/);
  } finally { globalThis.fetch = old; }
});
