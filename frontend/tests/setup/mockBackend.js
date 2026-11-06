// Backend mock untuk tes otomatis (src/services/mock/mockServer.js). Aplikasi sendiri selalu memanggil
// backend nyata (single gateway); di lingkungan tes (VITE_USE_MOCK=true) permintaan fetch dan
// XMLHttpRequest ke API_BASE_URL dijawab mock dengan kontrak yang sama. Tes yang memasang fetch sendiri
// (vi.stubGlobal) tetap memakai miliknya, dan vi.unstubAllGlobals mengembalikan pengalih ini.
import { API_BASE_URL } from '../../src/services/config';
import { handleMockRequest, subscribeMockEvents, subscribeMockWorkflowEvents } from '../../src/services/mock/mockServer';

const ORIGIN = 'http://localhost';
const apiBase = new URL(API_BASE_URL, ORIGIN).pathname.replace(/\/+$/, '');

/** { path, query } bila URL menuju API backend; null untuk URL lain. */
function apiTarget(url) {
  const parsed = new URL(url, ORIGIN);
  if (parsed.pathname !== apiBase && !parsed.pathname.startsWith(`${apiBase}/`)) return null;
  const query = Object.fromEntries(parsed.searchParams);
  return { path: parsed.pathname.slice(apiBase.length) || '/', query: Object.keys(query).length ? query : undefined };
}

async function answer(method, target, headers = {}, body) {
  const auth = headers.Authorization ?? headers.authorization;
  const token = auth ? auth.replace(/^Bearer\s+/i, '') : null;
  let payload = body;
  if (typeof body === 'string') {
    try {
      payload = JSON.parse(body);
    } catch {
      payload = body;
    }
  }
  const res = await handleMockRequest({ method, path: target.path, query: target.query, body: payload, token });
  return { status: res.status, text: res.data == null ? '' : JSON.stringify(res.data) };
}

if (import.meta.env.VITE_USE_MOCK === 'true') {
  const realFetch = globalThis.fetch;
  globalThis.fetch = async (input, init = {}) => {
    const url = typeof input === 'string' ? input : input.url;
    const target = apiTarget(url);
    if (!target) {
      if (!realFetch) throw new TypeError(`fetch ${url} tidak tersedia di lingkungan tes`);
      return realFetch(input, init);
    }
    const { status, text } = await answer((init.method ?? 'GET').toUpperCase(), target, init.headers, init.body);
    return { ok: status >= 200 && status < 300, status, text: async () => text, json: async () => (text ? JSON.parse(text) : null) };
  };

  // Unggah RPS memakai XMLHttpRequest demi laporan progres. Mock tidak mengirim data sungguhan, jadi progres
  // disimulasikan bertahap (maks. 90%) selama permintaan berjalan, lalu 100% setelah selesai.
  globalThis.XMLHttpRequest = class MockApiRequest {
    constructor() {
      this.upload = {};
      this.headers = {};
      this.status = 0;
      this.responseText = '';
    }

    open(method, url) {
      this.method = method.toUpperCase();
      this.url = url;
    }

    setRequestHeader(name, value) {
      this.headers[name] = value;
    }

    send(body) {
      const target = apiTarget(this.url);
      if (!target) {
        setTimeout(() => this.onerror?.());
        return;
      }
      let loaded = 0;
      const timer = setInterval(() => {
        loaded = Math.min(loaded + 15, 90);
        this.upload.onprogress?.({ lengthComputable: true, loaded, total: 100 });
      }, 60);
      answer(this.method, target, this.headers, body).then(
        ({ status, text }) => {
          clearInterval(timer);
          this.upload.onprogress?.({ lengthComputable: true, loaded: 100, total: 100 });
          this.status = status;
          this.responseText = text;
          this.onload?.();
        },
        () => {
          clearInterval(timer);
          this.onerror?.();
        },
      );
    }
  };

  // WebSocket ke /ws/workflows/{id} dan /ws/courses/{id} menerima event dari mock, sehingga klien
  // WebSocket sungguhan (monitoringSocket.js) ikut teruji. Jalur lain ditolak seperti handshake 4404.
  globalThis.WebSocket = class MockApiSocket {
    constructor(url) {
      this.url = url;
      this.readyState = 0;
      const parsed = new URL(url.replace(/^ws/, 'http'));
      const path = parsed.pathname.startsWith(`${apiBase}/`) ? parsed.pathname.slice(apiBase.length) : null;
      const workflow = path?.match(/^\/ws\/workflows\/([^/]+)$/);
      const course = path?.match(/^\/ws\/courses\/([^/]+)$/);
      const deliver = (frame) => this.readyState === 1 && this.onmessage?.({ data: JSON.stringify(frame) });
      if (!workflow && !course) {
        setTimeout(() => this.onclose?.({ code: 4404 }));
        return;
      }
      this.unsubscribe = workflow
        ? subscribeMockWorkflowEvents(decodeURIComponent(workflow[1]), deliver)
        : subscribeMockEvents(decodeURIComponent(course[1]), deliver);
      setTimeout(() => {
        if (this.readyState !== 0) return;
        this.readyState = 1;
        this.onopen?.();
      });
    }

    send() {}

    close() {
      if (this.readyState === 3) return;
      this.readyState = 3;
      this.unsubscribe?.();
      setTimeout(() => this.onclose?.({ code: 1000 }));
    }
  };
}
