export class WSClient {
  constructor(){ const proto = location.protocol === "https:" ? "wss" : "ws";
    this.url = `${proto}://${location.host}/ws`; this.ws = null; this.subscribedHz = 30; this.handlers = { view: [] }; }
  connect(){ this.ws = new WebSocket(this.url);
    this.ws.addEventListener("open",()=>{ this.send({ type:"subscribe", stream:"view", hz:this.subscribedHz }); });
    this.ws.addEventListener("message",(ev)=>{ try{ const msg = JSON.parse(ev.data); if (msg.type === "view"){ this.handlers.view.forEach(h=>h(msg.payload)); } } catch(e){} });
    this.ws.addEventListener("close",()=>{ setTimeout(()=>this.connect(), 1000); }); }
  onView(h){ this.handlers.view.push(h); } send(o){ if(this.ws && this.ws.readyState===WebSocket.OPEN){ this.ws.send(JSON.stringify(o)); } }
  toggle(){ this.send({type:"cmd", action:"toggle"}); } play(){ this.send({type:"cmd", action:"play"}); } pause(){ this.send({type:"cmd", action:"pause"}); }
  speed(v){ this.send({type:"cmd", action:"speed", value:v}); } add(c){ this.send({type:"cmd", action:"add_bees", count:c}); }
}
