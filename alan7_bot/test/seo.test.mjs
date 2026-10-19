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
    called.push({url, u});
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
    assert.equal(typeof called[0].url, 'string');
    assert.equal(called[0].u.searchParams.get('part'), 'snippet');
    assert.equal(called[0].u.searchParams.get('regionCode'), 'US');
    assert.equal(called[0].u.searchParams.get('relevanceLanguage'), 'en');
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
    assert.match(response, /HTTP 403/);
    assert.match(response, /Google refize/);
    assert.doesNotMatch(response, /secret-key/);
  } finally { globalThis.fetch = old; }
});


test('Google 400 API_KEY_INVALID is identified safely', async () => {
  const old = globalThis.fetch;
  globalThis.fetch = async () => Response.json({
    error: { code: 400, status: 'INVALID_ARGUMENT',
      message: 'API key SECRET_VALUE not valid. Please pass a valid API key.',
      details: [{ reason: 'API_KEY_INVALID', domain: 'googleapis.com' }] },
  }, { status: 400 });
  try {
    const response = await seoCommand({ YOUTUBE_API_KEY: 'SECRET_VALUE' }, 'es ballenas jorobadas');
    assert.match(response, /search.*HTTP 400.*API_KEY_INVALID/);
    assert.match(response, /Kle a pa valab/);
    assert.doesNotMatch(response, /SECRET_VALUE|googleapis\.com/);
  } finally { globalThis.fetch = old; }
});

test('Google disabled service error explains API project mismatch', async () => {
  const old = globalThis.fetch;
  globalThis.fetch = async () => Response.json({
    error: { status: 'PERMISSION_DENIED', details: [{ reason: 'SERVICE_DISABLED' }] },
  }, { status: 403 });
  try {
    const response = await seoCommand({ YOUTUBE_API_KEY: 'DONT_SHOW_ME' }, 'en cybersecurity');
    assert.match(response, /HTTP 403.*SERVICE_DISABLED/);
    assert.match(response, /pa aktive nan pwojè/);
    assert.doesNotMatch(response, /DONT_SHOW_ME/);
  } finally { globalThis.fetch = old; }
});

test('Quota exhaustion distinguishable from invalid API key', async () => {
  const old = globalThis.fetch;
  globalThis.fetch = async () => Response.json({
    error: { errors: [{ reason: 'quotaExceeded' }], message: 'SECRET_VALUE' },
  }, { status: 403 });
  try {
    const response = await seoCommand({ YOUTUBE_API_KEY: 'SECRET_VALUE' }, 'es jaguar');
    assert.match(response, /quotaExceeded/);
    assert.match(response, /Quota oswa limit/);
    assert.doesNotMatch(response, /SECRET_VALUE/);
  } finally { globalThis.fetch = old; }
});

test('Malformed error body never gets copied into the user-visible response', async () => {
  const old = globalThis.fetch;
  globalThis.fetch = async () => Response.json({
    error: { status: '<script>alert(1)</script>', message: 'API key SECRET_VALUE' },
  }, { status: 403 });
  try {
    const response = await seoCommand({ YOUTUBE_API_KEY: 'SECRET_VALUE' }, 'es selva');
    assert.match(response, /reason=unknown/);
    assert.doesNotMatch(response, /<script>|SECRET_VALUE/);
  } finally { globalThis.fetch = old; }
});


test('redirects never forward API key and show HTTP 3xx instead of generic NETWORK', async () => {
  const old = globalThis.fetch;
  let count = 0;
  globalThis.fetch = async (url, options) => {
    count++;
    assert.equal(typeof url, 'string');
    assert.equal(options.redirect, 'manual');
    return new Response(null, {status: 302, headers: { location: 'https://outside.invalid/collect' }});
  };
  try {
    const response = await seoCommand({YOUTUBE_API_KEY:'NEVER_EXPOSE_KEY'}, 'es ballenas');
    assert.equal(count, 1);
    assert.match(response, /HTTP 302.*REDIRECT/);
    assert.doesNotMatch(response, /NEVER_EXPOSE_KEY|outside\.invalid/);
  } finally { globalThis.fetch = old; }
});

test('network TypeError exposes safe class but no URL or key', async () => {
  const old = globalThis.fetch;
  globalThis.fetch = async () => { throw new TypeError('sensitive-secret-EXPOSE'); };
  try {
    const response = await seoCommand({YOUTUBE_API_KEY:'SENSITIVEKEY'}, 'es ballenas');
    assert.match(response, /NETWORK_TYPE_ERROR/);
    assert.doesNotMatch(response, /sensitive-secret-EXPOSE|SENSITIVEKEY/);
  } finally { globalThis.fetch = old; }
});
