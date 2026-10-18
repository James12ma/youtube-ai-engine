import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseVideoRequest, routeVideoRequest } from '../src/video_director.js';

test('runnable English job interview request; owner approval always required', () => {
  const route=routeVideoRequest(parseVideoRequest('5 types of job interviews | mode=full | lang=en | duration=60'));
  assert.equal(route.status,'render_supported');
  assert.equal(route.topic_id,'job-interviews');
  assert.equal(route.mode,'full');
  assert.equal(route.auto_publish,false);
  assert.equal(route.requires_owner_approval,true);
  assert.equal(route.ai_director,'not_connected');
});

test('preview test is a safe default', () => {
  const route=routeVideoRequest(parseVideoRequest('job-interviews'));
  assert.equal(route.mode,'preview');
  assert.equal(route.supported_now,true);
});

test('different subjects are accepted but not misrepresented as renderable', () => {
  for (const topic of [
    'How to write a resume',
    'Ce qui se passe en France',
    'Excel tutorial',
    'Wildlife documentary about whales',
    'Unregistered story'
  ]) {
    const route=routeVideoRequest(parseVideoRequest(topic));
    assert.equal(route.supported_now,false,topic);
    assert.equal(route.status,'awaiting_director',topic);
    assert.equal(route.auto_publish,false,topic);
  }
});

test('unsupported language, style and length do not trigger render', () => {
  for (const suffix of ['lang=fr','style=premium','duration=90']) {
    const route=routeVideoRequest(parseVideoRequest('job-interviews | '+suffix));
    assert.equal(route.supported_now,false,suffix);
  }
});

test('reject malformed, duplicate, overly large and control-character requests', () => {
  for (const request of [
    '', 'a'.repeat(500), 'foo | lang=en | language=fr',
    'foo | bad=anything', 'foo | duration=0', 'foo | mode=publish',
    'foo | lang=en\npublish=true'
  ]) {
    assert.throws(()=>parseVideoRequest(request),undefined,request.slice(0,30));
  }
});
