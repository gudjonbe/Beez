// Beez Metrics Client (Stats variables only)
(function(){
  if (window.__BEEZ_METRICS_CLIENT__) return;
  window.__BEEZ_METRICS_CLIENT__ = true;

  function el(id, make){
    var e = document.getElementById(id);
    if (!e && make) {
      e = document.createElement(make.tag || 'div');
      e.id = id;
      if (make.style) e.style.cssText = make.style;
      if (make.text) e.textContent = make.text;
      (make.parent || document.body).appendChild(e);
    }
    return e;
  }

  // Error surface
  window.addEventListener('error', function(ev){
    try {
      var box = el('metrics-error', { tag:'div', style:'position:fixed;left:8px;bottom:8px;max-width:60ch;padding:8px 10px;border-radius:6px;background:#7c2d12;color:#fff;font:12px/16px system-ui;z-index:9999;' });
      box.textContent = 'Metrics client error: ' + (ev && ev.message ? ev.message : 'unknown');
    } catch(e){}
  });

  var statusEl = el('status', { tag: 'div', style: 'position:fixed;top:8px;right:8px;padding:2px 8px;border-radius:4px;background:#1f2937;color:#e5e7eb;font:12px/20px system-ui;z-index:9999;', text: 'initializing...' });
  var statEl   = el('stats',  { tag: 'div', style: 'position:fixed;top:32px;right:8px;padding:2px 8px;border-radius:4px;background:#111827;color:#9ca3af;font:12px/20px system-ui;z-index:9999;' });
  var chartEl  = el('chart',  { tag: 'div', style: 'position:absolute;inset:48px 8px 8px 8px;min-height:200px;' });

  function needPlotly(){
    if (typeof window.Plotly === 'undefined') {
      statusEl.textContent = 'Plotly not loaded';
      statusEl.style.background = '#7c2d12';
      statusEl.title = 'Include Plotly on this page, e.g. <script src=\"https://cdn.plot.ly/plotly-2.35.2.min.js\" defer></script>';
      return true;
    }
    return false;
  }
  if (needPlotly()) return;

  // Build dropdown to toggle which Stats series to render (optional)
  var picker = el('series-picker', { tag:'div', style:'position:fixed;left:8px;top:8px;display:flex;gap:8px;flex-wrap:wrap;max-width:70vw;z-index:9999;' });
  function mkChip(id, label, checked){
    var w = document.createElement('label');
    w.style.cssText = 'display:inline-flex;align-items:center;gap:6px;padding:4px 8px;border-radius:999px;background:#0b0f14;color:#cbd5e1;border:1px solid #1f2937;cursor:pointer;font:12px/16px system-ui;';
    var cb = document.createElement('input'); cb.type = 'checkbox'; cb.id = id; cb.checked = !!checked;
    var span = document.createElement('span'); span.textContent = label;
    w.appendChild(cb); w.appendChild(span);
    picker.appendChild(w);
  }

  // Whitelist mapping: internal key -> label
  var WANTED = {
    'bees.count':                'Bees',
    'world.flowers_remaining':   'Flowers left',
    'world.total_deposited':     'Nectar deposited',
    'stats.roles.forager':       'Roles: forager',
    'stats.roles.queen':         'Roles: queen',
    'stats.signals.brood':       'Signals: brood',
    'stats.signals.queen_mandibular': 'Signals: queen mandibular',
    'stats.signals.tremble':     'Signals: tremble',
    'stats.signals.waggle':      'Signals: waggle',
    'stats.receiver_queue':      'Receiver queue',
    'stats.queue_avg':           'Queue avg',
    'stats.waggle_active':       'Active waggles',
    'stats.receivers_active':    'Receivers active'
  };

  // Initial selection: turn on the most interesting ones; you can toggle chips
  var DEFAULT_ON = {
    'bees.count': true,
    'world.flowers_remaining': true,
    'world.total_deposited': true,
    'stats.roles.forager': true,
    'stats.signals.waggle': true,
    'stats.receiver_queue': true,
    'stats.queue_avg': true,
    'stats.waggle_active': true
  };

  // Build chips
  Object.keys(WANTED).forEach(function(k){
    mkChip('chip:'+k, WANTED[k], !!DEFAULT_ON[k]);
  });

  try {
    window.Plotly.newPlot(chartEl, [], {
      paper_bgcolor:'rgba(0,0,0,0)',
      plot_bgcolor:'#0b0f14',
      font:{color:'#e6edf3'},
      margin:{l:56,r:12,t:12,b:44},
      legend:{orientation:'h',bgcolor:'rgba(0,0,0,0)'},
      xaxis:{title:'Sim time (s)', gridcolor:'#203040', zeroline:false},
      yaxis:{gridcolor:'#203040', zeroline:false, autorange:true}
    }, {responsive:true, displayModeBar:false});
  } catch (e) {
    statusEl.textContent = 'Plot init failed';
    console.error(e);
    return;
  }

  function isNum(n){ return typeof n === 'number' && Number.isFinite(n); }

  function flatten(obj, prefix){
    prefix = prefix || '';
    var out = {};
    if (!obj || typeof obj !== 'object') return out;
    for (var k in obj) {
      if (!Object.prototype.hasOwnProperty.call(obj,k)) continue;
      var v = obj[k];
      var key = prefix ? (prefix + '.' + k) : k;
      if (v && typeof v === 'object' && !Array.isArray(v)) {
        var sub = flatten(v, key);
        for (var sk in sub) if (Object.prototype.hasOwnProperty.call(sub, sk)) out[sk] = sub[sk];
      } else if (typeof v === 'number' || typeof v === 'string' || typeof v === 'boolean') {
        out[key] = v;
      }
    }
    return out;
  }

  function pickFrame(obj){
    if (!obj || typeof obj !== 'object') return null;
    if (obj && obj.type && obj.payload) return obj.payload;
    if (obj && obj.view) return obj.view;
    if (obj && obj.state) return obj.state;
    if (obj && obj.frame) return obj.frame;
    return obj;
  }

  // Trace registry
  var traces = Object.create(null);
  var order = [];
  function ensureTrace(name, label){
    if (traces[name]) return traces[name].idx;
    var idx = order.length;
    order.push(name);
    traces[name] = { idx: idx, label: label || name };
    window.Plotly.addTraces(chartEl, [{ x:[], y:[], name: (label || name), mode:'lines' }]);
    return idx;
  }

  var proto = location.protocol === 'https:' ? 'wss' : 'ws';
  var base = (location.pathname.replace(/\/(?:metrics(?:\.html)?)?$/, '')) || '';
  var PRIMARY = proto + '://' + location.host + base + '/ws/metrics';
  var FALLBACK = proto + '://' + location.host + base + '/ws';

  var ws = null, usingFallback = false, reconnectTimer = null;
  var lastT = null, fallbackT = 0, frames = 0, t0 = performance.now();

  function computeDerived(frame, flat){
    var out = {};

    // bee count
    if (frame && Array.isArray(frame.bees)) out['bees.count'] = frame.bees.length;

    // allow either stats.queue_avg or world.queue_avg etc.
    out['world.flowers_remaining'] = (flat['world.flowers_remaining']);
    out['world.total_deposited']   = (flat['world.total_deposited']);

    out['stats.roles.forager'] = flat['stats.roles.forager'];
    out['stats.roles.queen']   = flat['stats.roles.queen'];

    out['stats.signals.brood']            = flat['stats.signals.brood'];
    out['stats.signals.queen_mandibular'] = flat['stats.signals.queen_mandibular'];
    out['stats.signals.tremble']          = flat['stats.signals.tremble'];
    out['stats.signals.waggle']           = flat['stats.signals.waggle'];

    out['stats.receiver_queue'] = (flat['stats.receiver_queue'] != null ? flat['stats.receiver_queue'] : flat['world.hive_queue']);
    out['stats.queue_avg']      = (flat['stats.queue_avg'] != null ? flat['stats.queue_avg'] : flat['world.queue_avg']);
    out['stats.waggle_active']  = (flat['stats.waggle_active'] != null ? flat['stats.waggle_active'] : flat['world.waggle_active']);
    out['stats.receivers_active'] = flat['stats.receivers_active'];

    // Prune to only numeric
    var pruned = {};
    for (var k in out) if (isNum(out[k])) pruned[k] = out[k];
    return pruned;
  }

  function pickTime(flat){
    var cands = ['t','time','simtime','sim_time','stats.t','stats.time','stats.simtime'];
    for (var i=0;i<cands.length;i++){
      var k = cands[i];
      if (isNum(flat[k])) return flat[k];
    }
    for (var k in flat){ if (k.toLowerCase().indexOf('time')>=0 && isNum(flat[k])) return flat[k]; }
    return null;
  }

  function connect(url, isFallback){
    isFallback = !!isFallback;
    usingFallback = isFallback;
    if (ws) { try { ws.close(); } catch (e){} }
    statusEl.textContent = 'connecting...';
    statusEl.style.background = '#1f2937';

    try { ws = new WebSocket(url); }
    catch (e) { statusEl.textContent = 'WS failed'; scheduleReconnect(true); return; }

    ws.onopen = function(){
      statusEl.textContent = 'live';
      statusEl.style.background = '#064e3b';
      if (usingFallback) {
        try { ws.send(JSON.stringify({ type:'subscribe', stream:'view', hz:20 })); } catch (e){}
      }
    };
    ws.onclose = function(){ statusEl.textContent = 'closed'; statusEl.style.background = '#374151'; scheduleReconnect(false); };
    ws.onerror = function(){ statusEl.textContent = 'error';  statusEl.style.background = '#7c2d12'; if (!usingFallback) scheduleReconnect(true); else scheduleReconnect(false); };

    ws.onmessage = function(ev){
      var raw; try { raw = JSON.parse(ev.data); } catch (e) { return; }
      var frame = pickFrame(raw);
      var flat  = flatten(frame);
      var t = pickTime(flat); if (!isNum(t)) { t = (++fallbackT); if (lastT === t) t = (++fallbackT); } lastT = t;

      var derived = computeDerived(frame, flat);
      // Filter to wanted + currently selected chips
      var keys = [];
      for (var k in WANTED) {
        var selected = (document.getElementById('chip:'+k) && document.getElementById('chip:'+k).checked);
        if (selected && isNum(derived[k])) keys.push(k);
      }
      if (keys.length === 0) return;

      var idxs = [];
      for (var i=0;i<keys.length;i++) idxs.push(ensureTrace(keys[i], WANTED[keys[i]]));

      var x = new Array(keys.length);
      var y = new Array(keys.length);
      for (var j=0;j<keys.length;j++){
        x[j] = [t];
        y[j] = [derived[keys[j]]];
      }
      try {
        window.Plotly.extendTraces(chartEl, { x: x, y: y }, idxs, 2000);
      } catch (e) {
        console.error('extendTraces failed', e);
        var box = el('metrics-error', { tag:'div', style:'position:fixed;left:8px;bottom:8px;max-width:60ch;padding:8px 10px;border-radius:6px;background:#7c2d12;color:#fff;font:12px/16px system-ui;z-index:9999;' });
        box.textContent = 'extendTraces failed: ' + (e && e.message ? e.message : e);
        return;
      }

      frames++;
      var now = performance.now();
      if (now - t0 > 1000) {
        var fps = (frames * 1000 / (now - t0)).toFixed(1);
        statEl.textContent = fps + ' fps · ' + order.length + ' traces';
        frames = 0; t0 = now;
      }
    };
  }

  function scheduleReconnect(forceFallback){
    if (reconnectTimer) return;
    reconnectTimer = setTimeout(function(){
      reconnectTimer = null;
      if (forceFallback) connect(FALLBACK, true);
      else connect(usingFallback ? FALLBACK : PRIMARY, usingFallback);
    }, 1000);
  }

  connect(PRIMARY, false);
})();
