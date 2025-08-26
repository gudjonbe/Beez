// WebSocket client for the "view" stream + simple command helpers.
export class WSClient {
  constructor() {
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
    this.url = `${protocol}://${location.host}/ws`;
    this.ws = null;
    this.subscribedHz = 30;
    this.handlers = { view: [] };
  }

  connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) return;
    this.ws = new WebSocket(this.url);

    this.ws.addEventListener('open', () => {
      this.send({ type: 'subscribe', stream: 'view', hz: this.subscribedHz });
    });

    this.ws.addEventListener('message', (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg?.type === 'view') this.handlers.view.forEach((h) => h(msg.payload));
      } catch (err) {
        console.warn('WS message parse error:', err);
      }
    });

    this.ws.addEventListener('close', () => setTimeout(() => this.connect(), 1000));
    this.ws.addEventListener('error', (err) => console.error('WebSocket error:', err));
  }

  onView(handler) { this.handlers.view.push(handler); }
  send(obj) { if (this.ws && this.ws.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify(obj)); }

  // ---- Command helpers ----
  toggle() { this.send({ type: 'cmd', action: 'toggle' }); }
  play()   { this.send({ type: 'cmd', action: 'play'   }); }
  pause()  { this.send({ type: 'cmd', action: 'pause'  }); }
  speed(v) { this.send({ type: 'cmd', action: 'speed', value: v }); }

  // Add bees with an optional kind ("worker" | "queen" | "drone")
  add(count, kind = 'worker') {
    this.send({ type: 'cmd', action: 'add_bees', count, kind });
  }
}

