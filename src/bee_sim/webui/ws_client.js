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
      } catch (err) { console.warn('WS message parse error:', err); }
    });
    this.ws.addEventListener('close', () => setTimeout(() => this.connect(), 1000));
    this.ws.addEventListener('error', (err) => console.error('WebSocket error:', err));
  }
  onView(handler) { this.handlers.view.push(handler); }
  send(obj) { if (this.ws && this.ws.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify(obj)); }

  toggle() { this.send({ type: 'cmd', action: 'toggle' }); }
  play()   { this.send({ type: 'cmd', action: 'play'   }); }
  pause()  { this.send({ type: 'cmd', action: 'pause'  }); }
  speed(v) { this.send({ type: 'cmd', action: 'speed', value: v }); }

  add(count, kind = 'worker') {
    this.send({ type: 'cmd', action: 'add_bees', count, kind });
  }
  addFlowers(count) {
    this.send({ type: 'cmd', action: 'add_flowers', count });
  }
  addFlowerAt(x, y, n = 1) {
    this.send({ type: 'cmd', action: 'add_flower_at', x, y, n });
  }
}
