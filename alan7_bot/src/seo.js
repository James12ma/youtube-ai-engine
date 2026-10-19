// Read-only owner-requested SEO lookup. No GitHub minutes, scraper, upload or scheduled requests.
// YOUTUBE_API_KEY is a Cloudflare secret and MUST NOT be returned, persisted or logged.
const ROOT = 'https://www.googleapis.com/youtube/v3';

const escapeHTML = (s) => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;')
  .replace(/>/g, '&gt;').replace(/"/g, '&quot;');

async function publicAPI(env, endpoint, params) {
  if (!['search', 'videos', 'channels'].includes(endpoint)) return null;
  const url = new URL(ROOT + '/' + endpoint);
  for (const [key, val] of Object.entries(params)) url.searchParams.set(key, String(val));
  url.searchParams.set('key', env.YOUTUBE_API_KEY);
  try {
    const result = await fetch(url, { method: 'GET', redirect: 'error',
      headers: { accept: 'application/json' } });
    if (!result.ok) return null;
    const payload = await result.json();
    return payload && Array.isArray(payload.items) ? payload.items : null;
  } catch {
    return null;
  }
}

// A Telegram owner command, not an LLM instruction. /seo es ballenas, /seo en cybersecurity.
// The YouTube regionCode parameter limits video availability, NOT viewer location.
export async function seoCommand(env, raw) {
  const input = String(raw || '').trim();
  const match = /^(?:(en|es)\s+)?([\s\S]{3,120})$/i.exec(input);
  if (!match) return 'Itilize: <code>/seo es ballenas jorobadas</code> oswa <code>/seo en cybersecurity</code>.';
  const lang = (match[1] || 'es').toLowerCase();
  const topic = match[2].trim();
  if (topic.length < 3 || topic.length > 120 || /[<>]/.test(topic)) {
    return 'Sijè a dwe genyen ant 3 ak 120 karaktè, san HTML.';
  }
  if (!env.YOUTUBE_API_KEY) {
    return '⚠️ SEO live poko aktive: mete YOUTUBE_API_KEY nan Cloudflare Secrets. Pa voye kle a sou Telegram.';
  }
  const search = await publicAPI(env, 'search', {
    part: 'id', type: 'video', maxResults: '5', q: topic, regionCode: 'US',
    relevanceLanguage: lang, safeSearch: 'moderate',
  });
  if (!search) return '⚠️ YouTube API pa disponib oswa quota rive nan limit. Pa gen done SEO envante.';
  const ids = [...new Set(search.map((i) => i && i.id && i.id.videoId).filter(
    (id) => typeof id === 'string' && /^[a-zA-Z0-9_-]{11}$/.test(id)))].slice(0, 5);
  if (!ids.length) return 'Pa gen videyo piblik nan rezilta rechèch sa a.';
  const videos = await publicAPI(env, 'videos', {
    part: 'snippet,statistics', id: ids.join(','),
  });
  if (!videos) return '⚠️ Statistik videyo yo pa disponib. Pa gen rezilta envante.';
  const channelsIDs = [...new Set(videos.map((v) => v?.snippet?.channelId).filter(
    (id) => typeof id === 'string' && /^UC[a-zA-Z0-9_-]{22}$/.test(id)))];
  const channels = channelsIDs.length ? await publicAPI(env, 'channels', {
    part: 'snippet,statistics', id: channelsIDs.join(','),
  }) : [];
  const byChannel = new Map((channels || []).map((c) => [c.id, c]));
  const result = [
    '<b>SEO Intelligence — OWNER REVIEW</b>',
    'Sijè: ' + escapeHTML(topic),
    'Lang: ' + lang + ' | Search region: US',
    '⚠️ US search pa vle di viewers yo soti USA.',
  ];
  for (const id of ids.slice(0, 4)) {
    const video = videos.find((v) => v.id === id);
    if (!video) continue;
    const title = String(video.snippet?.title || 'Untitled').slice(0, 100);
    const views = video.statistics?.viewCount ?? 'pa disponib';
    const channel = byChannel.get(video.snippet?.channelId);
    const subs = channel?.statistics?.subscriberCount ?? 'pa disponib';
    const tags = (video.snippet?.tags || []).filter((t) => typeof t === 'string').slice(0, 5);
    result.push(
      '\n<b>' + escapeHTML(title) + '</b>',
      'Views: ' + escapeHTML(views) + ' | Channel subs: ' + escapeHTML(subs),
      'Tags piblik: ' + (tags.length ? escapeHTML(tags.join(', ')) : 'pa disponib'),
      'https://www.youtube.com/watch?v=' + id,
    );
  }
  result.push('\n<b>Pwopozisyon pou revizyon:</b> ' + escapeHTML(topic),
    'Sa yo se done piblik, pa prediksyon sou views oswa revni.',
    'Pa gen okenn videyo ki pibliye. Tit ak tags bezwen apwobasyon ou.');
  return result.join('\n').slice(0, 3800);
}
