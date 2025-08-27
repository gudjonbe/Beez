// WebSocket client for the "view" stream + simple command helpers.
export class WSClient {
  constructor() {
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
    this.url = `${protocol}://${location.host}/ws`;

    /** @type {WebSocket|null} */
    this.ws = null;

    /** Update rate for the "view" stream (Hz). */
    this.subscribedHz = 30;

    /** Registered handlers for incoming "view" messages. */
    this.handlers = { view: [] };
  }

  connect() {
    this.ws = new WebSocket(this.url);

    this.ws.addEventListener('open', () => {
      this.send({ type: 'subscribe', stream: 'view', hz: this.subscribedHz });
    });

    this.ws.addEventListener('message', (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg?.type === 'view') {
          this.handlers.view.forEach((h) => h(msg.payload));
        }
      } catch (err) {
        console.warn('WS message parse error:', err);
      }
    });

    this.ws.addEventListener('close', () => {
      setTimeout(() => this.connect(), 1000);
    });

    this.ws.addEventListener('error', (err) => {
      console.error('WebSocket error:', err);
    });
  }

  /** Add a handler for "view" payloads. */
  onView(handler) {
    this.handlers.view.push(handler);
  }

  /** Send a JSON message if the socket is open. */
  send(obj) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(obj));
    }
  }

  // ---- Command helpers ----
  toggle() { this.send({ type: 'cmd', action: 'toggle' }); }
  play()   { this.send({ type: 'cmd', action: 'play'   }); }
  pause()  { this.send({ type: 'cmd', action: 'pause'  }); }
  speed(v) { this.send({ type: 'cmd', action: 'speed', value: v }); }
  add(count=1, kind='worker') { this.send({ type: 'cmd', action: 'add_bees', count, kind }); }
  addFlowers(count=10) { this.send({ type: 'cmd', action: 'add_flowers', count }); }
  addFlowerAt(x, y, n=1) { this.send({ type: 'cmd', action: 'add_flower_at', x, y, n }); }
}
