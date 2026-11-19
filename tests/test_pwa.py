"""PWA delivery and offline-isolation checks; no model or network downloads."""

from html.parser import HTMLParser
import io
import json
from pathlib import Path
import shutil
import subprocess
import unittest

from PIL import Image

from app import app


ROOT = Path(__file__).resolve().parents[1]


class _HeadParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.scripts = []
        self.meta = {}

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == "link":
            self.links.append(attrs)
        elif tag == "script" and attrs.get("src"):
            self.scripts.append(attrs["src"])
        elif tag == "meta" and attrs.get("name"):
            self.meta[attrs["name"]] = attrs.get("content", "")


class PWADeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def test_home_announces_install_assets_and_apple_icon(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        parser = _HeadParser()
        parser.feed(response.get_data(as_text=True))
        links = {(link.get("rel"), link.get("href")) for link in parser.links}
        self.assertIn(("manifest", "/static/manifest.webmanifest"), links)
        self.assertIn(("stylesheet", "/static/mobile.css"), links)
        self.assertIn(("apple-touch-icon", "/static/icons/apple-touch-icon.png"), links)
        self.assertIn("/static/mobile.js", parser.scripts)
        self.assertTrue(parser.meta.get("theme-color"))
        self.assertEqual(parser.meta.get("apple-mobile-web-app-capable"), "yes")

    def test_manifest_defines_same_origin_standalone_app_and_real_icons(self):
        response = self.client.get("/static/manifest.webmanifest")
        self.assertEqual(response.status_code, 200)
        self.assertIn(response.mimetype, {"application/manifest+json", "application/json"})
        manifest = json.loads(response.get_data(as_text=True))
        self.assertTrue(manifest.get("name"))
        self.assertTrue(manifest.get("short_name"))
        self.assertEqual(manifest["start_url"], "/")
        self.assertEqual(manifest["scope"], "/")
        self.assertEqual(manifest["display"], "standalone")
        sizes_and_purposes = set()
        for icon in manifest["icons"]:
            with self.subTest(icon=icon["src"]):
                self.assertTrue(icon["src"].startswith("/static/icons/"))
                image_response = self.client.get(icon["src"])
                self.assertEqual(image_response.status_code, 200)
                self.assertEqual(image_response.mimetype, "image/png")
                with Image.open(io.BytesIO(image_response.data)) as image:
                    self.assertEqual(image.format, "PNG")
                    declared_sizes = icon["sizes"].split()
                    actual_size = "{}x{}".format(*image.size)
                    self.assertIn(actual_size, declared_sizes)
                    for purpose in icon.get("purpose", "any").split():
                        sizes_and_purposes.add((actual_size, purpose))
        self.assertTrue({("192x192", "any"), ("512x512", "any"),
                         ("512x512", "maskable")}.issubset(sizes_and_purposes))

    def test_mobile_assets_and_offline_page_are_served_with_usable_types(self):
        for path, allowed_types in (
            ("/static/mobile.css", {"text/css"}),
            ("/static/mobile.js", {"text/javascript", "application/javascript"}),
            ("/static/icons/apple-touch-icon.png", {"image/png"}),
            ("/offline.html", {"text/html"}),
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn(response.mimetype, allowed_types)
                self.assertTrue(response.data)
        offline = self.client.get("/offline.html").get_data(as_text=True).lower()
        self.assertIn("offline", offline)
        self.assertTrue("reconnect" in offline or "connection" in offline)

    def test_worker_is_served_at_root_and_revalidated(self):
        response = self.client.get("/service-worker.js")
        self.assertEqual(response.status_code, 200)
        self.assertIn(response.mimetype, {"text/javascript", "application/javascript"})
        self.assertIn("no-cache", response.headers.get("Cache-Control", ""))
        # A root URL gives the worker a default scope of '/', covering all screens.
        self.assertNotIn("<html", response.get_data(as_text=True).lower())

    @unittest.skipUnless(shutil.which("node"), "Node is needed to execute the worker isolation check")
    def test_worker_preserves_live_requests_and_only_falls_back_on_network_failure(self):
        response = self.client.get("/service-worker.js")
        self.assertEqual(response.status_code, 200)
        result = subprocess.run(
            [shutil.which("node"), "--input-type=commonjs", "-e", _WORKER_HARNESS],
            input=response.get_data(as_text=True),
            text=True,
            capture_output=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("worker behavior passed", result.stdout)


_WORKER_HARNESS = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const origin = 'http://localhost:7872';
const events = {};
const stored = new Map();
const writes = [];
const deletions = [];
const pathOf = request => new URL(typeof request === 'string' ? request : request.url, origin).pathname;
const caches = {
  async open(name) {
    if (!stored.has(name)) stored.set(name, new Map());
    const entries = stored.get(name);
    return {
      async add(request) {
        const path = pathOf(request);
        writes.push(path);
        entries.set(path, new Response('offline fixture: reconnect to Choob'));
      },
      async addAll(requests) { for (const request of requests) await this.add(request); },
      async put(request, response) { writes.push(pathOf(request)); entries.set(pathOf(request), response.clone()); },
      async match(request) { return entries.get(pathOf(request))?.clone(); }
    };
  },
  async match(request) {
    for (const entries of stored.values()) {
      const response = entries.get(pathOf(request));
      if (response) return response.clone();
    }
  },
  async keys() { return [...stored.keys(), 'unrelated-team-cache']; },
  async delete(name) { deletions.push(name); return stored.delete(name); }
};
let offline = false;
let fetches = 0;
const context = {
  self: {
    location: new URL(origin + '/service-worker.js'),
    registration: {scope: origin + '/'},
    clients: {async claim() {}},
    async skipWaiting() {},
    addEventListener(type, handler) { (events[type] ||= []).push(handler); }
  },
  caches,
  URL,
  Request,
  Response,
  Headers,
  console,
  async fetch() {
    fetches++;
    if (offline) throw new Error('simulated network disconnection');
    return new Response('fresh network response', {status: 200});
  }
};
vm.runInNewContext(fs.readFileSync(0, 'utf8'), context);

async function lifecycle(type) {
  const pending = [];
  for (const handler of events[type] || []) handler({waitUntil(promise) { pending.push(promise); }});
  await Promise.all(pending);
}
function request(path, method = 'GET', mode = 'navigate') {
  return {url: new URL(path, origin).href, method, mode,
          destination: mode === 'navigate' ? 'document' : '', headers: new Headers()};
}
function dispatch(req) {
  let intercepted;
  for (const handler of events.fetch || []) handler({
    request: req,
    respondWith(promise) { assert.equal(intercepted, undefined); intercepted = Promise.resolve(promise); },
    waitUntil() {}
  });
  return intercepted;
}
(async () => {
  assert.ok(events.fetch?.length, 'worker needs a fetch listener');
  await lifecycle('install');
  await lifecycle('activate');
  assert.ok(writes.includes('/offline.html'), 'offline fallback must be available after installation');
  assert.ok(!writes.includes('/'), 'never cache the app HTML, which could freeze teammates\' updates');
  assert.ok(writes.every(path => !path.startsWith('/api/')), 'never cache AI responses');
  assert.ok(!deletions.includes('unrelated-team-cache'), 'do not delete caches owned by other apps');

  for (const req of [request('/api/status', 'GET', 'cors'),
                     request('/api/discover/chat', 'POST', 'cors'),
                     request('/', 'POST'),
                     request('https://other.example/meal')]) {
    assert.equal(dispatch(req), undefined, 'API, mutations and cross-origin requests must bypass this worker');
  }
  const before = fetches;
  const onlineResponse = await dispatch(request('/'));
  assert.ok(onlineResponse, 'online navigation should go through the network-first fallback');
  assert.equal(await onlineResponse.text(), 'fresh network response');
  assert.ok(fetches > before);
  assert.ok(!writes.includes('/'), 'online navigation must not be saved to a stale shell cache');

  offline = true;
  const offlineResponse = await dispatch(request('/'));
  assert.ok(offlineResponse, 'navigation should have an offline fallback');
  assert.match(await offlineResponse.text(), /offline fixture/);
  assert.ok(writes.every(path => !path.startsWith('/api/')));
  console.log('worker behavior passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
"""


if __name__ == "__main__":
    unittest.main()
