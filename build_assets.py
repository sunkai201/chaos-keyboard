# -*- coding: utf-8 -*-
"""
把 Key Quota 网页游戏改造成 Android 输入法可用的资产。
只做三件事：
  1) 注入 IME 适配 CSS（去 header、压缩、加草稿条）
  2) 注入 JS 桥接 shim（KQ.type / KQ.del / KQ.hit）
  3) 改 type / erase / renderChat / 转盘结算，让文字真的进输入框
广告、换弹、转盘、配额机制全部原样保留。
"""
import os, sys, re

SRC = r"C:\Users\47469\Documents\xwechat_files\wxid_qti85viqsmb612_7857\msg\file\2026-11\KeyQuota-Blind-Phone.html"
DST = r"C:\Users\47469\Documents\deepseek-harness\default-workspace\KeyQuotaIME\app\src\main\assets\keyquota.html"

html = open(SRC, encoding="utf-8").read()
orig_len = len(html)

def rep(old, new, tag):
    global html
    if old not in html:
        print("  [MISS] " + tag)
        return False
    html = html.replace(old, new, 1)
    print("  [OK]   " + tag)
    return True

print("source %d bytes" % orig_len)

# ---------------------------------------------------------------- 1. CSS
IME_CSS = """
/* ================= IME 适配层（原生输入法注入） ================= */
html,body{height:100%!important;margin:0!important;overflow:hidden!important}
body{display:flex!important;flex-direction:column!important}
header{display:none!important}
main{height:100%!important;width:100%!important;max-width:100%!important;
     padding:0!important;margin:0!important;flex:1 1 auto!important;min-height:0!important}
.heading{display:none!important}
#chat{flex:1 1 auto!important;min-height:0!important;border-radius:0!important;
      border-left:0!important;border-right:0!important;border-bottom:0!important;
      border-top:0!important;box-shadow:none!important}
#chat .bar{height:24px!important;padding:0 10px!important;font-size:11px!important}
#chat #log{flex:0 0 58px!important;min-height:58px!important;max-height:58px!important}
#empty{display:none!important}
#chat .keyboard{flex:1 1 auto!important;min-height:0!important;
                padding:3px 3px 5px!important;gap:3px!important}
.keyboard .keyhead{min-height:22px!important;font-size:11px!important;
                   margin:0 3px 2px!important;gap:6px!important}
.keyhead small{font-size:10px!important}
.keyhead .func{width:36px!important;height:22px!important;font-size:15px!important}
.keyboard #rows{border-radius:2px!important}
.actions{gap:4px!important}
.actions button{height:30px!important;font-size:13px!important}
#send{padding:0 12px!important}
#rows #space small{font-size:.62em!important}
/* 草稿条：盲打模式也能看见自己敲了什么 */
#draftbar{flex:none!important;height:26px!important;line-height:18px!important;
          overflow:hidden!important;white-space:nowrap!important;
          text-overflow:ellipsis!important;direction:ltr!important;
          text-align:left!important;
          font:13px/18px var(--mono)!important;color:#FFE2A4!important;
          background:#241a39!important;border-top:1px solid #6d4c5e!important;
          padding:4px 10px!important}
#draftbar:empty:before{content:'盲打中 · 打完点「发送」进转盘';color:#7d6e85!important;font-size:11px!important}
/* 宿主应用标签 */
#hostTag{font-style:normal!important;font-size:10px!important;color:#A8E2B0!important;
         margin-left:auto!important;padding-left:8px!important;opacity:.9!important;
         white-space:nowrap!important}
/* 广告区在全屏 stage 里，保持原样只在高度上兜底 */
#ad .poster{overflow:auto!important}
@media(max-height:520px){
  #ad .adcard video{height:min(38vh,220px)!important}
}
/* 转盘 / 广告 / 换弹 改成浮层：盖在键盘上方，键盘本身不销毁、不重排 */
main{position:relative!important}
#reload,#ad,#game{position:absolute!important;left:0!important;right:0!important;
  top:0!important;bottom:0!important;z-index:30!important;
  background:#171127!important;border:0!important;box-shadow:none!important}
</style>"""
rep("</style></head><body>", IME_CSS + "</head><body>", "css")

# ---------------------------------------------------------------- 2. 草稿条 DOM
rep(
    '<div id="log" role="log"><div id="empty"><strong>还没有发出的消息</strong></div><div id="messages"></div></div>',
    '<div id="log" role="log"><div id="empty"><strong>还没有发出的消息</strong></div><div id="messages"></div></div><div id="draftbar"></div>',
    "draftbar")

# ---------------------------------------------------------------- 3. 宿主标签
rep(
    '<div class="keyhead"><b>混沌键盘 <span>/ 碰撞区</span></b><small>键帽数字为剩余次数</small></div>',
    '<div class="keyhead"><b>混沌键盘</b><small>数字=剩余次数</small><i id="hostTag"></i></div>',
    "hostTag")

# ---------------------------------------------------------------- 4. JS shim
SHIM = r"""
/* ================= 原生输入法桥接 ================= */
var KQ = {
  n: (typeof KQNative !== 'undefined' && KQNative) ? KQNative : null,
  /* 打字阶段不上屏，只更新游戏内草稿 */
  type: function (ch) { },
  /* 点「发送」：整句写进待输入框，返回是否成功 */
  commit: function (t) {
    if (!this.n || !t) return false;
    try { return !!KQNative.commitText(t); } catch (e) { return false; }
  },
  /* 转盘未命中：把整句从待输入框撤回 */
  del:  function (n)  { if (this.n && n > 0) { try { KQNative.deleteBack(n); } catch (e) {} } },
  /* 转盘命中：尝试触发发送 */
  hit:  function (t)  { if (this.n) { try { KQNative.onCommitted(t || ''); } catch (e) {} } },
  buzz: function ()   { if (this.n) { try { KQNative.haptic(); } catch (e) {} } },
  log:  function (m)  { if (this.n) { try { KQNative.log(String(m)); } catch (e) {} } }
};
window.KQ = KQ;

window.KQSetHost = function (label, pkg) {
  var el = document.getElementById('hostTag');
  if (el) el.textContent = label ? ('→ ' + label) : '';
};

/* 切换输入框时由原生调用：清掉未完成草稿，避免串字 */
window.KQReset = function () {
  try {
    if (typeof phase !== 'undefined' && phase === 'chat') {
      draft = '';
      renderChat();
    }
  } catch (e) {}
};
"""
rep("</main><script>'use strict';", "</main><script>'use strict';\n" + SHIM, "js-shim")

# ---------------------------------------------------------------- 5. type() 只更新草稿
rep(
"""function type(c){
  if(phase!=='chat' || (c!==' ' && !remaining[c])) return;
  draft+=uppercase?c.toUpperCase():c;
  if(c!==' ' && --remaining[c]===0){depleted=c;phase='depleted'}
  renderChat();
}""",
"""function type(c){
  if(phase!=='chat' || (c!==' ' && !remaining[c])) return;
  var ch=uppercase?c.toUpperCase():c;
  draft+=ch;                                    /* 打字阶段只进游戏内草稿，不上屏 */
  if(c!==' ' && --remaining[c]===0){depleted=c;phase='depleted'}
  KQ.buzz();
  renderChat();
}""",
    "type()")

# ---------------------------------------------------------------- 6. erase() 撤回
rep(
"""function erase(){
  if(!chatPhase() || !triple()) return;
  draft='';
  renderChat();
}""",
"""function erase(){
  if(!chatPhase() || !triple()) return;
  draft='';                                     /* 文字还没进输入框，直接清草稿 */
  renderChat();
}""",
    "erase()")

# ---------------------------------------------------------------- 7. renderChat 同步草稿条
rep(
"""  if(depleted) $('offer').textContent='点击此处获取【'+depleted.toUpperCase()+'】次数';
}""",
"""  if(depleted) $('offer').textContent='点击此处获取【'+depleted.toUpperCase()+'】次数';
  var db=document.getElementById('draftbar');
  if(db) db.textContent=draft;
}""",
    "renderChat()")

# ---------------------------------------------------------------- 8. 转盘结算
rep(
"""againBtn.onclick=()=>{
  if(phase!=='dial' || !gameState.over) return;
  if(gameState.feedback!=='hit'){phase='chat';hideOverlay();show('chat');renderChat();return}
  const message=document.createElement('p');message.className='message';message.textContent=pending;
  $('messages').append(message);$('empty').hidden=true;
  $('count').textContent=String(++messageCount).padStart(2,'0')+' 条已发送';
  draft='';pending='';phase='chat';hideOverlay();show('chat');renderChat();
  $('log').scrollTop=$('log').scrollHeight;
};""",
"""againBtn.onclick=()=>{
  if(phase!=='dial' || !gameState.over) return;
  if(gameState.feedback!=='hit'){
    /* 未命中：把刚才写进待输入框的整句撤回 */
    if(pending.length) KQ.del(pending.length);
    draft='';pending='';phase='chat';hideOverlay();show('chat');renderChat();
    return
  }
  const message=document.createElement('p');message.className='message';message.textContent=pending;
  $('messages').append(message);$('empty').hidden=true;
  $('count').textContent=String(++messageCount).padStart(2,'0')+' 条已发出';
  KQ.hit(pending);                              /* ← 命中：触发发送 */
  draft='';pending='';phase='chat';hideOverlay();show('chat');renderChat();
  $('log').scrollTop=$('log').scrollHeight;
};""",
    "againBtn")

# ---------------------------------------------------------------- 9. 发送：整句落到待输入框
rep(
"""press($('send'),()=>{
  if(phase!=='chat' || !draft.trim()) return;
  if(!ctx){""",
"""press($('send'),()=>{
  if(phase!=='chat' || !draft.trim()) return;
  KQ.buzz();
  /* 整句写进待输入框；写失败就不进退盘，避免撤回时误删原有文字 */
  if(!KQ.commit(draft)) return;
  if(!ctx){""",
    "send-commit")

# ---------------------------------------------------------------- 11. 键盘永不隐藏
# 原版 show() 会把 #chat 一起 display:none，转盘出现时整个键盘被替换，
# 看起来像"输入法退出去了"。改成只切换浮层，#chat 永远保留。
rep(
"""function show(screen){
  for (const name of ['chat','reload','ad','game']) $(name).hidden=name!==screen;
}""",
"""function show(screen){
  /* #chat 常驻，转盘/广告/换弹以浮层覆盖，键盘物理位置不重置 */
  const overlay = ['reload','ad','game'];
  for (const name of overlay) $(name).hidden = (name!==screen);
  $('chat').hidden = false;
}""",
    "show-overlay")

# ---------------------------------------------------------------- 12. 删除键常亮
# 原版删除键只在「三连相同字符」时才可用，平时一直是灰的。
# 改成：有草稿就能按，每次退一个字符。
rep(
"""function erase(){
  if(!chatPhase() || !triple()) return;
  draft='';                                     /* 文字还没进输入框，直接清草稿 */
  renderChat();
}""",
"""function erase(){
  if(!chatPhase() || !draft.length) return;
  draft=draft.slice(0,-1);                      /* 退掉最后一个字符 */
  renderChat();
}""",
    "erase-single")

rep(
"""  $('del').disabled=!chatPhase() || !triple();""",
"""  $('del').disabled=false;                      /* 常亮：任何时候都能按 */""",
    "del-enabled")
# 原版 Bug：抽奖第一次就失败 → 看广告 → settle() 因 earned===0 直接 return，
# phase 永久停在 'ad'，所有按键变灰、无法返回（用户看到的就是"键一直是灰的"）。
# 修复：广告看完但一次都没抽中时，退回换弹界面继续抽。
rep(
"""function settle(){
  if(!depleted || !earned || !(phase==='ad' || (phase==='reload' && !busy))) return;
  remaining[depleted]+=earned;
  depleted=null;earned=0;busy=false;phase='chat';show('chat');renderChat();
}""",
"""function settle(){
  if(!depleted) return;
  if(!(phase==='ad' || (phase==='reload' && !busy))) return;
  if(earned<=0){
    busy=false;phase='reload';show('reload');ready('没抽中，再点卡槽试一次');
    return;
  }
  remaining[depleted]+=earned;
  depleted=null;earned=0;busy=false;phase='chat';show('chat');renderChat();
}""",
    "settle-deadlock")

# ---------------------------------------------------------------- 13. 需求二：命中只上屏，不发送
# 点 Send 只是进轮盘，不写输入框；命中才 commit；未命中什么都不做。
# 这样既不会触发宿主发送，也不会让宿主收起键盘。
rep(
"""  KQ.buzz();
  /* 整句写进待输入框；写失败就不进退盘，避免撤回时误删原有文字 */
  if(!KQ.commit(draft)) return;
  if(!ctx){""",
"""  KQ.buzz();
  if(!ctx){""",
    "send-no-commit")

rep(
"""  if(gameState.feedback!=='hit'){
    /* 未命中：把刚才写进待输入框的整句撤回 */
    if(pending.length) KQ.del(pending.length);
    draft='';pending='';phase='chat';hideOverlay();show('chat');renderChat();
    return
  }""",
"""  if(gameState.feedback!=='hit'){
    /* 未命中：什么都没上屏，直接回键盘 */
    draft='';pending='';phase='chat';hideOverlay();show('chat');renderChat();
    return
  }""",
    "miss-no-rollback")

rep(
"""  $('count').textContent=String(++messageCount).padStart(2,'0')+' 条已发出';
  KQ.hit(pending);                              /* ← 命中：触发发送 */""",
"""  $('count').textContent=String(++messageCount).padStart(2,'0')+' 条已上屏';
  KQ.commit(pending);                           /* ← 命中：只上屏，不发送 */""",
    "hit-commit-only")

# ---------------------------------------------------------------- 14. 需求三：删除键作用于宿主
# 草稿非空 → 退草稿；草稿为空 → 交给原生删宿主输入框（含 emoji 安全）
rep(
"""function erase(){
  if(!chatPhase() || !draft.length) return;
  draft=draft.slice(0,-1);                      /* 退掉最后一个字符 */
  renderChat();
}""",
"""function erase(){
  if(!chatPhase()) return;
  if(draft.length){
    draft=draft.slice(0,-1);                    /* 先退草稿 */
    renderChat();
    return;
  }
  KQ.del(1);                                    /* 草稿空：删宿主输入框 */
}""",
    "erase-host")

# 长按连删：400ms 后开始，每 50ms 一次，抬起/取消立即停止
rep(
"""for (const key of document.querySelectorAll('#rows [data-char]')){""",
"""(function(){
  var btn=$('del'), t=null, iv=null;
  function stop(){ if(t){clearTimeout(t);t=null} if(iv){clearInterval(iv);iv=null} }
  btn.addEventListener('pointerdown',function(e){
    if(e.cancelable) e.preventDefault();
    stop();
    t=setTimeout(function(){ iv=setInterval(erase,50); },400);
  });
  /* Listen in the capture phase on window: the button's own pointerup is
     often swallowed inside a WebView, which would make the timer delete forever. */
  ['pointerup','pointercancel','pointerout','touchend','touchcancel','mouseup','blur']
    .forEach(function(ev){ window.addEventListener(ev, stop, true); });
  document.addEventListener('visibilitychange', function(){ if(document.hidden) stop(); });
})();

for (const key of document.querySelectorAll('#rows [data-char]')){""",
    "del-longpress")

# ---------------------------------------------------------------- 11. 全英文（界面 + 注释）
# 严格按术语表翻译：Commit / Send / Delete / Space / Wheel / Hit / Reload / Claim ...
# 长串优先，避免 "发送" 先被替换而破坏 "发送并返回"。
EN_MAP = [
    # ---- 长句 / 整句 ----
    ("此页面需要执行 JavaScript 才能打字。请用能运行本地 HTML 的浏览器打开文件，或在 Safari / Chrome 中访问此文件的网页地址。",
     "JavaScript is required. Open this HTML file in a browser that can run scripts."),
    ("转盘 / 广告 / 换弹 改成浮层：盖在键盘上方，键盘本身不销毁、不重排",
     "wheel / ad / reload are overlays: the keyboard is never destroyed"),
    ("广告区在全屏 stage 里，保持原样只在高度上兜底",
     "ad stage: keep the layout, only cap the height"),
    ("草稿条：盲打模式也能看见自己敲了什么",
     "draft bar: shows what you typed in blind mode"),
    ("切换输入框时由原生调用：清掉未完成草稿，避免串字",
     "called by native on input switch: drop the unfinished draft"),
    ("整句写进待输入框；写失败就不进退盘，避免撤回时误删原有文字",
     "commit the line; abort the wheel if commit fails"),
    ("未命中：把刚才写进待输入框的整句撤回",
     "miss: nothing was committed"),
    ("点「发送」：整句写进待输入框，返回是否成功",
     "Send: commit the whole line, returns success"),
    ("转盘未命中：把整句从待输入框撤回",
     "wheel miss: roll back the committed line"),
    ("打字阶段不上屏，只更新游戏内草稿",
     "typing only updates the in-game draft"),
    ("打字阶段只进游戏内草稿，不上屏",
     "draft only, no commit while typing"),
    ("当前查看器无法绘制指针，请使用支持 Canvas 的浏览器。",
     "Canvas is required to draw the pointer."),
    ("盲打模式 · 每个字符初始 3 次", "Blind Mode · 3 uses per key"),
    ("盲打中 · 打完点「发送」进转盘", "Blind mode · Tap Send for the Wheel"),
    ("时间耗尽 · 输入已清空", "Time Up · Input Cleared"),
    ("未命中 · 继续点击", "Miss · Tap Again"),
    ("转盘命中：尝试触发发送", "wheel hit: commit to the host input"),
    ("点击卡槽，开始换弹", "Tap slot to reload"),
    ("再装一发，或完成换弹", "Load again or finish"),
    ("没抽中，再点卡槽试一次", "Missed. Try again"),
    ("指针进入红区时按下", "Tap in the Red Zone"),
    ("IME 适配层（原生输入法注入）", "IME adaptation layer"),
    ("#chat 常驻，转盘/广告/换弹以浮层覆盖，键盘物理位置不重置",
     "#chat stays mounted; overlays cover it"),
    # ---- 中句 ----
    ("当前仅显示静态预览", "Static Preview Only"),
    ("键盘启动失败", "Keyboard failed to start"),
    ("正在启动键盘…", "Starting keyboard…"),
    ("数字=剩余次数", "Number = Uses Left"),
    ("切换大写输入", "Toggle uppercase"),
    ("完成换弹 ↗", "Finish Reload ↗"),
    ("点击此处获取【", "Tap to get "),
    ("打开 X 登录页", "Open X login page"),
    ("发送并返回", "Commit"),
    ("返回键盘", "Back"),
    ("字符总余量", "Characters Left"),
    ("还没有发出的消息", "No messages yet"),
    ("下一发成功率", "Next Chance"),
    ("尝试命中红区", "Tap the red zone"),
    ("清空本次输入", "Clear input"),
    ("常亮：任何时候都能按", "always enabled"),
    ("退掉最后一个字符", "remove last character"),
    ("按下判定", "Tap to Judge"),
    ("原生输入法桥接", "native IME bridge"),
    # ---- 短词 ----
    ("字符换弹", "Reload"), ("模拟广告", "Ad"), ("发送校准", "Wheel"),
    ("消息记录", "Message Log"), ("混沌键盘", "Chaos Keyboard"),
    ("盲打模式", "Blind Mode"), ("本局结果", "Result"),
    ("装填演示", "Loading…"), ("装填成功", "Loaded"), ("卡槽受阻", "Jammed"),
    ("播放视频", "Play Video"), ("已获得", "Earned"),
    ("秒后可查收", "s to claim"), ("广告已结束", "Ad finished"),
    ("条已发送", "Sent"), ("条已发出", "Sent"), ("条已上屏", "Committed"),
    ("时间耗尽", "Time Up"), ("输入已清空", "Input Cleared"),
    ("时间到", "Time's Up"), ("未命中", "Miss"), ("继续点击", "Tap Again"),
    ("在此输入英文消息…", "Type a message…"),
    ("待 查 收", "Claim"), ("待查收", "Claim"),
    ("发送", "Send"), ("命中", "Hit"), ("小写", "Lower"), ("大写", "Upper"),
    ("剩余", "uses left"), ("次数", " uses"), ("剩余次数", "uses left"),
]

for zh, en in EN_MAP:
    html = html.replace(zh, en)

# aria-label 里的拼接："glyph+'，剩余 '+n+' 次'"
html = html.replace("'，剩余 '+remaining[c]+' 次'", "' + remaining[c] + ' uses left'")
# 计数行："00 条已发送" 已被替换为 "00 Sent"；JS 侧 " 条已发出" 同上
# 广告倒计时 "seconds+' 秒后可查收'"
html = html.replace("seconds+' 秒后可查收'", "seconds + 's to claim'")
# 错误行 "（第 '+e.lineno+' 行）"
html = html.replace("'（第 '+e.lineno+' 行）'", "' (line ' + e.lineno + ')'")
# offer 文案 "点击此处获取【X】次数"
html = html.replace("'点击此处获取【'+depleted.toUpperCase()+'】次数'",
                    "'Tap to get ' + depleted.toUpperCase() + ' uses'")
# 替换顺序造成的残留："】 uses" -> " uses"
html = html.replace("】 uses", " uses")
html = html.replace("【", "").replace("】", "")
html = html.replace("「", "'").replace("」", "'")

# 剩余零散中文（注释 + aria 拼接）
html = html.replace("/* 宿主应用标签 */", "/* host app tag */")
html = html.replace("glyph+'，uses left '+remaining[c]+' 次'",
                    "glyph + ' · ' + remaining[c] + ' uses left'")
html = html.replace("/* 先退草稿 */", "/* delete from draft first */")
html = html.replace("/* 草稿空：删宿主输入框 */", "/* draft empty: delete from host input */")
html = html.replace("/* Miss：什么都没上屏，直接回键盘 */",
                    "/* Miss: nothing committed, back to keyboard */")
html = html.replace("/* ← Hit：只上屏，不Send */", "/* <- Hit: commit only, never send */")

# ================================================================
# Change 1: Message log -> suggestion bar
# Drop #messages / #count / #empty; add #suggest / #undoBar.
# Total keyboard height unchanged (#log stays 58px, #rows untouched).
# ================================================================

# ---- 1. dom ----
rep(
'<div class="bar"><b><i class="light"></i> Message Log</b><span id="count">00 Sent</span></div>\n'
'<div id="log" role="log"><div id="empty"><strong>No messages yet</strong></div><div id="messages"></div></div><div id="draftbar"></div>',
'<div class="bar"><b><i class="light"></i> Suggestions</b><span id="sentCount">SENT 00</span></div>\n'
'<div id="log" role="toolbar" aria-label="Word suggestions"><div id="suggest"></div><div id="undoBar" hidden></div></div><div id="draftbar"></div>',
    "suggest-dom")

# ---- 2. drop old css ----
rep("#chat #log{flex:0 0 clamp(34px,7vh,66px);min-height:0}#empty{min-height:0}#empty strong{font-size:12px}",
    "#chat #log{flex:0 0 clamp(34px,7vh,66px);min-height:0}",
    "css-log")

rep("#empty strong{color:#ffe2a4}#empty small{color:#cbbed2}", "", "css-empty-color")

rep("#messages{display:flex;flex-direction:column;align-items:flex-end;gap:9px;padding:0 16px}#messages:not(:empty){padding-block:14px}.message{margin:0;border-radius:12px 12px 2px 12px;border:1px solid #c2c6ee;background:#e8ebff;padding:9px 14px;max-width:85%}.message,#draft,.preview p{",
    "#draft,.preview p{",
    "css-messages")

rep("@media(max-height:450px){header,.heading p,.keyhead,#empty small{display:none}",
    "@media(max-height:450px){header,.heading p,.keyhead{display:none}",
    "css-mq-empty")

# 我之前的 IME 适配层里有一条 #empty{display:none!important}，一并清掉
rep("#empty{display:none!important}\n", "", "css-empty-ime")

# ---- 3. suggestion css ----
rep("""/* wheel / ad / reload are overlays: the keyboard is never destroyed */
main{position:relative!important}""",
"""/* suggestions bar: replaces the old message log */
#suggest{display:flex!important;gap:5px!important;height:100%!important;
  overflow-x:auto!important;overflow-y:hidden!important;padding:4px 6px!important;
  scrollbar-width:none!important}
#suggest::-webkit-scrollbar{display:none!important}
#suggest button{flex:0 0 auto!important;min-width:64px!important;height:100%!important;
  border:1px solid #a8dcff!important;border-radius:2px!important;
  background:#3659b8!important;color:#ffebbb!important;
  font:600 13px/1.1 var(--mono)!important;padding:0 10px!important;
  white-space:nowrap!important;box-shadow:none!important}
#suggest button:disabled{opacity:.4!important}
#suggest button:active:enabled{background:#864058!important}
#undoBar{position:absolute!important;left:0!important;right:0!important;
  top:0!important;bottom:0!important;z-index:6!important;
  display:flex!important;align-items:center!important;gap:6px!important;
  background:#241a39!important;padding:4px 8px!important;
  font:600 12px var(--mono)!important;color:#a8e2b0!important}
#undoBar[hidden]{display:none!important}
#log{position:relative!important}
#undoBar button{border:1px solid #a8e2b0!important;border-radius:2px!important;
  background:#2c4a3a!important;color:#d7f387!important;font:600 12px var(--mono)!important;
  padding:0 10px!important;height:100%!important}
/* wheel / ad / reload are overlays: the keyboard is never destroyed */
main{position:relative!important}""",
    "css-suggest")

# ---- 4. js: word list ----
rep("let phase='chat', draft='', depleted=null, earned=0, busy=false, messageCount=0;",
"""let phase='chat', draft='', depleted=null, earned=0, busy=false, sentCount=0;

/* ===== change 1: word list by first letter ===== */
const SUGGEST_WORDS = {
  a:['about','after','again','all','also','always','and','another','any','app','are','around','ask','at','available','away'],
  b:['back','be','because','before','best','better','big','book','but','buy','by'],
  c:['call','can','case','change','check','city','close','code','coffee','come','could'],
  d:['day','did','do','does','done','down','during'],
  e:['each','early','easy','eat','end','enough','even','evening','every'],
  f:['family','far','fast','few','find','first','food','for','friend','from','full'],
  g:['game','get','give','go','good','great','group'],
  h:['had','has','have','he','help','her','here','him','his','home','how'],
  i:['if','in','into','is','it','its'],
  j:['just'],
  k:['keep','kind','know'],
  l:['last','late','learn','left','less','let','life','like','little','look','lot','love'],
  m:['make','many','may','me','meet','message','might','mine','more','most','move','much','must','my'],
  n:['name','need','never','new','next','night','no','not','now','number'],
  o:['of','off','on','once','one','only','open','or','other','our','out','over','own'],
  p:['page','part','people','place','plan','play','please','point','put'],
  q:['question','quick','quite'],
  r:['read','ready','real','really','right','room','run'],
  s:['said','same','say','see','send','she','should','show','side','since','small','so','some','soon','still','such','sure'],
  t:['take','talk','tell','than','that','the','their','them','then','there','these','they','thing','think','this','those','time','to','today','together','too','try','two'],
  u:['under','until','up','us','use'],
  v:['very'],
  w:['wait','want','was','way','we','well','went','were','what','when','where','which','while','who','why','will','with','word','work','would','write'],
  x:[], y:['year','yes','you','your'], z:[]
};
/* fallback candidates */
const DEFAULT_SUGGEST = ['meet','send','today','later','thanks'];
let suggestionNonce = 0;""",
    "js-wordlist")

# ---- 5. js: render and tap ----
rep("""  var db=document.getElementById('draftbar');
  if(db) db.textContent=draft;
}""",
"""  var db=document.getElementById('draftbar');
  if(db) db.textContent=draft;
  renderSuggestions();
  paintRainbow();
}

/* ===== Rainbow theme: one colour per keycap, contrast border ===== */
const RAINBOW_COLORS = ['#FF2D2D','#FF7A00','#FFD700','#22C55E',
                        '#22D3EE','#3B82F6','#8B5CF6','#EC4899'];

function paintRainbow(){
  if(document.documentElement.dataset.theme !== 'rainbow') return;
  var keys = document.querySelectorAll('#rows .key');
  for(var i = 0; i < keys.length; i++){
    keys[i].style.setProperty('--kbg', RAINBOW_COLORS[i % RAINBOW_COLORS.length]);
    keys[i].style.setProperty('--kbd', RAINBOW_COLORS[(i + 3) % RAINBOW_COLORS.length]);
    /* random negative delay so no two keys flash in sync */
    if(!keys[i].dataset.strobe){
      keys[i].dataset.strobe = '1';
      keys[i].style.animationDelay = (-Math.random() * 0.4).toFixed(2) + 's';
      keys[i].style.animationDuration = (0.05 + Math.random() * 0.06).toFixed(2) + 's';
    }
  }
}

/* ===== change 1: suggestions ===== */
function currentPrefix(){
  var m = draft.match(/[a-z]+$/i);
  return m ? m[0] : '';
}

function renderSuggestions(){
  var box = document.getElementById('suggest');
  if(!box) return;
  var typing = (phase === 'chat');
  var prefix = currentPrefix();
  var typed = prefix.toLowerCase();

  /* 还没输入任何东西：候选栏保持空白 */
  if(!draft.trim()){
    box.replaceChildren();
    return;
  }

  var picked = [];
  function push(w){
    if(!w || picked.length >= 5) return;
    if(picked.indexOf(w) < 0) picked.push(w);
  }

  /* 1) 前缀匹配最多 3 个 */
  if(typed){
    var bucket = SUGGEST_WORDS[typed.charAt(0)] || [];
    for(var i=0;i<bucket.length && picked.length<3;i++){
      if(bucket[i].indexOf(typed) === 0 && bucket[i] !== typed) push(bucket[i]);
    }
  }
  /* 2) only the empty draft uses generic words; with a prefix, stay on-prefix */
  if(!typed){
    for(var j=0;j<DEFAULT_SUGGEST.length && picked.length<5;j++) push(DEFAULT_SUGGEST[j]);
  }
  /* 3) pad to at least 4, on-prefix when possible */
  if(picked.length < 4){
    if(typed && config.interferenceEnabled){
      var fill = pickPolluted(typed, 5 - picked.length, picked);
      for(var f=0;f<fill.length;f++) push(fill[f]);
    }else{
      for(var k=0;k<DEFAULT_SUGGEST.length && picked.length<4;k++) push(DEFAULT_SUGGEST[k]);
    }
  }

  box.replaceChildren();
  for(var n=0;n<picked.length;n++){
    var b = document.createElement('button');
    b.type = 'button';
    b.textContent = picked[n];
    b.disabled = !typing;
    b.addEventListener('click', (function(word){
      return function(){ applySuggestion(word); };
    })(picked[n]));
    box.appendChild(b);
  }
}

/* replace prefix + append space; no quota */
function applySuggestion(word){
  if(phase !== 'chat' || !word) return;
  var prefix = currentPrefix();
  var start = draft.length - prefix.length;
  var capped = (start === 0) ? (word.charAt(0).toUpperCase() + word.slice(1)) : word;
  draft = draft.slice(0, start) + capped + ' ';
  KQ.buzz();
  renderChat();
}""",
    "js-render-suggest")

# ---- 6. hit branch: drop list, keep SENT ----
rep("""  const message=document.createElement('p');message.className='message';message.textContent=pending;
  $('messages').append(message);$('empty').hidden=true;
  $('count').textContent=String(++messageCount).padStart(2,'0')+' Committed';
  KQ.commit(pending);                           /* <- Hit: commit only, never send */
  draft='';pending='';phase='chat';hideOverlay();show('chat');renderChat();
  $('log').scrollTop=$('log').scrollHeight;""",
"""  sentCount++;
  $('sentCount').textContent='SENT '+String(sentCount).padStart(2,'0');
  KQ.commit(pending);                           /* <- Hit: commit only, never send */
  draft='';pending='';phase='chat';hideOverlay();show('chat');renderChat();""",
    "js-hit-count")

# 第二套主题里残留的旧规则（#empty 与 .message）
rep("#empty{height:100%;min-height:60px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px}#empty strong{font-size:14px}#empty small{font-size:12px;color:var(--muted)}",
    "", "css-empty-block")
rep(".message{background:#34325e;color:#fff0bd;border:1px solid #cfb7b7;border-radius:3px;box-shadow:2px 2px #171125}",
    "", "css-message-theme")

# ---- 7. render once on boot ----
rep("startKeyboard();\nrenderChat();", "startKeyboard();\nrenderChat();\nrenderSuggestions();", "js-boot-suggest")

# ================================================================
# Change 3: KEY-CONFLICT interference layer (deletable)
# ================================================================

# ---- A. config ----
rep("const config = {decay:0.75, animationMs:620, adMs:5000, freezeMs:500, arc:[30,50], speed:[180,270]};",
"""const config = {decay:0.75, animationMs:620, adMs:5000, freezeMs:500, arc:[30,50], speed:[180,270]};

/* ===== KEY-CONFLICT interference layer (delete to restore) ===== */
config.interferenceEnabled = true;   /* master switch */
config.motionEnabled = true;         /* false for Chalk: keys stay in a static grid */
config.interruptEveryMin = 5;        /* words per interrupt ad (min) */
config.interruptEveryMax = 8;        /* max */
config.interruptChance = 1.0;        /* chance to fire at zero */
config.deleteHijackChance = 0.15;    /* delete hijack chance */

/* brand words that hijack suggestions */
const WORD_SWAP = {
  code:'codex', app:'appflow', talk:'talkhub', chat:'chatly', mail:'maildesk',
  meet:'meetly', call:'callbridge', send:'sendloop', note:'notely', plan:'planbase',
  work:'workgrid', team:'teamloop', task:'taskly', file:'filehub', sync:'syncpro',
  cloud:'cloudly', data:'datahive', link:'linkly', share:'sharely', post:'postly',
  text:'textly', word:'wordly', page:'pageflow', shop:'shopwave', pay:'payport'
};

/* ad creatives (from Key-Conflict) */
const CAMPAIGNS = [
  {keywords:/\\b(pizzas?|burgers?|dinner|lunch|food|hungry|takeout)\\b/i, score:98, name:'Slice Sprint', title:'Pizza break?', copy:'A hot slice could get there before your next message.'},
  {keywords:/\\b(pizzas?|dinner|lunch|food)\\b/i, score:74, name:'Meal Parade', title:'Dinner plans?', copy:'Get meal ideas while your message waits.'},
  {keywords:/\\b(flights?|airports?|travel|hotels?|vacation|trips?)\\b/i, score:97, name:'CloudHop', title:'Compare flight deals', copy:'Find a seat before you finish your sentence.'},
  {keywords:/\\b(coffee|latte|cafe|espresso)\\b/i, score:96, name:'Grand Brew Cafe', title:'Coffee first?', copy:'A little caffeine for the rest of that message.'},
  {keywords:/\\b(games?|gaming|esports|xbox|playstation|switch)\\b/i, score:95, name:'PixelPass', title:'Game night awaits', copy:'Discover a new game during this brief keyboard break.'},
  {keywords:/\\b(movies?|films?|cinema|tv|streaming)\\b/i, score:94, name:'Reel Room', title:'Movie night picks', copy:'Find a movie while your keyboard takes an intermission.'},
  {keywords:/\\b(books?|library|study|homework|school|class)\\b/i, score:93, name:'Page Pop', title:'One more chapter?', copy:'Browse study picks while your draft waits.'}
].sort(function(first, second){ return second.score - first.score; });

let wordsUntilAd = rollAdDelay();
let pendingDelete = false;
let deleteHijackedThisRound = false;
let undoState = null;
let undoTimer = null;

function rollAdDelay(){
  var min = config.interruptEveryMin, max = config.interruptEveryMax;
  return min + Math.floor(Math.random() * (max - min + 1));
}

function contextWords(text){ return text.toLowerCase().match(/[a-z0-9]+/g) || []; }

function pickAd(text){
  var words = contextWords(text).slice(-8);
  for(var i = words.length - 1; i >= 0; i--){
    for(var c = 0; c < CAMPAIGNS.length; c++){
      if(CAMPAIGNS[c].keywords.test(words[i])) return CAMPAIGNS[c];
    }
  }
  return {name:'Trend Flash', title:'A trending break', copy:'Trend Flash has a roundup of what everyone is talking about.'};
}

/* 选污染候选：必须跟随当前前缀，不能随机跳词。
   前缀能对上既有品牌词就用它，否则按前缀动态拼一个公司名。
   用 hash 保证同一个前缀每次结果稳定，不会每敲一个键就闪。 */
const BRAND_SUFFIX = ['hub','flow','pro','base','cloud','go','pay','ai','link','point',
  'space','one','plus','max','core','net','lab','works','studio','now','tech','soft',
  'wave','byte','loop','stack','grid','forge','pulse','nova'];

function hashStr(s){
  var h = 0;
  for(var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return Math.abs(h);
}

/* 品牌 / 广告语词典：支持精确、模糊（编辑距离）、包含三种匹配。
   keys 是用户可能敲出来的样子，word 是最终塞进候选的公司名或广告语。 */
const BRAND_DICT = [
  /* fashion / luxury */
  {keys:['prada','pand','pnda'], word:'prada'},
  {keys:['gucci','guc','guci'], word:'gucci'},
  {keys:['chanel','chan','shanel'], word:'chanel'},
  {keys:['dior','diorr'], word:'dior'},
  {keys:['versace','vers'], word:'versace'},
  {keys:['armani','arma'], word:'armani'},
  {keys:['burberry','burb'], word:'burberry'},
  {keys:['hermes','herm'], word:'hermes'},
  {keys:['rolex','rol'], word:'rolex'},
  {keys:['omega','ome'], word:'omega'},
  {keys:['zara','zar'], word:'zara'},
  {keys:['uniqlo','uniq'], word:'uniqlo'},
  {keys:['nike','nkie'], word:'nike'},
  {keys:['adidas','adid'], word:'adidas'},
  {keys:['puma','pum'], word:'puma'},
  {keys:['reebok','reeb'], word:'reebok'},
  {keys:['lululemon','lemon','lulu','lemo'], word:'lululemon'},
  {keys:['levis','levi'], word:'levis'},
  {keys:['guerlain','guer'], word:'guerlain'},

  /* tech / internet */
  {keys:['apple','appl','iphone','ipho'], word:'apple'},
  {keys:['google','goog','gogle'], word:'google'},
  {keys:['microsoft','micro','msft'], word:'microsoft'},
  {keys:['amazon','amaz','amzn'], word:'amazon'},
  {keys:['facebook','face'], word:'meta'},
  {keys:['netflix','netf','netflx'], word:'netflix'},
  {keys:['tesla','tesl'], word:'tesla'},
  {keys:['nvidia','nvid','nvida'], word:'nvidia'},
  {keys:['intel','inte'], word:'intel'},
  {keys:['samsung','sams'], word:'samsung'},
  {keys:['sony','sonyy'], word:'sony'},
  {keys:['openai','open'], word:'openai'},
  {keys:['twitter','twit','tweet'], word:'twitter'},
  {keys:['tiktok','tik'], word:'tiktok'},
  {keys:['spotify','spot','spotfy'], word:'spotify'},
  {keys:['uber','uberr'], word:'uber'},
  {keys:['airbnb','airb'], word:'airbnb'},
  {keys:['paypal','payp'], word:'paypal'},
  {keys:['stripe','stri'], word:'stripe'},
  {keys:['adobe','adob'], word:'adobe'},
  {keys:['oracle','orac'], word:'oracle'},
  {keys:['salesforce','sales'], word:'salesforce'},
  {keys:['cisco','cisc'], word:'cisco'},
  {keys:['dell','delll'], word:'dell'},
  {keys:['lenovo','leno'], word:'lenovo'},
  {keys:['asus','asuss'], word:'asus'},
  {keys:['acer','acerr'], word:'acer'},
  {keys:['nokia','nok'], word:'nokia'},
  {keys:['motorola','moto'], word:'motorola'},
  {keys:['xiaomi','xiao'], word:'xiaomi'},
  {keys:['huawei','huaw'], word:'huawei'},
  {keys:['oppo','oppoo'], word:'oppo'},
  {keys:['vivo','vivoo'], word:'vivo'},
  {keys:['oneplus','onepl'], word:'oneplus'},
  {keys:['alibaba','alib','ali'], word:'alibaba'},
  {keys:['tencent','tenc'], word:'tencent'},
  {keys:['baidu','baid'], word:'baidu'},
  {keys:['meituan','meit'], word:'meituan'},
  {keys:['bytedance','byte','douyin'], word:'bytedance'},
  {keys:['dji','dron'], word:'dji'},
  {keys:['nio','nioauto'], word:'nio'},
  {keys:['xpeng','xpen'], word:'xpeng'},

  /* food / drinks */
  {keys:['starbucks','star','buck'], word:'starbucks'},
  {keys:['mcdonalds','mcd'], word:'mcdonalds'},
  {keys:['kfc','kentucky'], word:'kfc'},
  {keys:['burgerking','burger'], word:'burgerking'},
  {keys:['subway','subw'], word:'subway'},
  {keys:['pizzahut','pizza'], word:'pizzahut'},
  {keys:['dominos','domi'], word:'dominos'},
  {keys:['cocacola','coke','cola'], word:'cocacola'},
  {keys:['pepsi','peps'], word:'pepsi'},
  {keys:['nestle','nest'], word:'nestle'},
  {keys:['heineken','hein'], word:'heineken'},
  {keys:['budweiser','budw'], word:'budweiser'},
  {keys:['redbull','redb'], word:'redbull'},
  {keys:['nescafe','nesc'], word:'nescafe'},
  {keys:['dove','dovee'], word:'dove'},

  /* auto */
  {keys:['toyota','toyo'], word:'toyota'},
  {keys:['honda','hond'], word:'honda'},
  {keys:['mercedes','merc','benz'], word:'mercedes'},
  {keys:['audi','audii'], word:'audi'},
  {keys:['porsche','pors'], word:'porsche'},
  {keys:['ferrari','ferr'], word:'ferrari'},
  {keys:['lamborghini','lamb'], word:'lamborghini'},
  {keys:['volkswagen','volks'], word:'volkswagen'},
  {keys:['volvo','volv'], word:'volvo'},
  {keys:['nissan','niss'], word:'nissan'},
  {keys:['mazda','mazd'], word:'mazda'},
  {keys:['hyundai','hyun'], word:'hyundai'},

  /* retail / ecommerce */
  {keys:['walmart','walm'], word:'walmart'},
  {keys:['costco','cost'], word:'costco'},
  {keys:['ikea','ikeaa'], word:'ikea'},
  {keys:['target','targ'], word:'target'},
  {keys:['ebay','ebayy'], word:'ebay'},
  {keys:['shopify','shopf'], word:'shopify'},
  {keys:['taobao','taob'], word:'taobao'},
  {keys:['tmall','tmal'], word:'tmall'},
  {keys:['pinduoduo','pind'], word:'pinduoduo'},
  {keys:['shein','shei'], word:'shein'},

  /* finance */
  {keys:['visa','visaa'], word:'visa'},
  {keys:['mastercard','master'], word:'mastercard'},
  {keys:['amex','americ'], word:'amex'},
  {keys:['hsbc','hsbcc'], word:'hsbc'},
  {keys:['jpmorgan','jpm'], word:'jpmorgan'},
  {keys:['goldman','gold'], word:'goldman'},
  {keys:['citibank','citi'], word:'citi'},
  {keys:['alipay','alip'], word:'alipay'},

  /* media / entertainment */
  {keys:['disney','disn','disny'], word:'disney'},
  {keys:['warner','warn'], word:'warner'},
  {keys:['universal','univ'], word:'universal'},
  {keys:['marvel','marv'], word:'marvel'},
  {keys:['pixar','pixa'], word:'pixar'},
  {keys:['youtube','yout'], word:'youtube'},
  {keys:['instagram','insta'], word:'instagram'},

  /* travel */
  {keys:['emirates','emir'], word:'emirates'},
  {keys:['lufthansa','luf'], word:'lufthansa'},
  {keys:['delta','delt'], word:'delta'},
  {keys:['marriott','marr'], word:'marriott'},
  {keys:['hilton','hilt'], word:'hilton'},
  {keys:['hyatt','hyat'], word:'hyatt'},
  {keys:['booking','book'], word:'booking'},

  /* sport */
  {keys:['northface','north'], word:'thenorthface'},
  {keys:['columbia','colu'], word:'columbia'},
  {keys:['underarmour','under'], word:'underarmour'},
  {keys:['newbalance','newb'], word:'newbalance'},
  {keys:['asics','asic'], word:'asics'},

  /* beauty */
  {keys:['sephora','seph'], word:'sephora'},
  {keys:['loreal','lore'], word:'loreal'},
  {keys:['maybelline','mayb'], word:'maybelline'},

  /* fictional tech brands used as the ad inventory */
  {keys:['code','cod'], word:'codex'},
  {keys:['app'], word:'appflow'},
  {keys:['talk','chat'], word:'talkhub'},
  {keys:['mail'], word:'maildesk'},
  {keys:['meet'], word:'meetly'},
  {keys:['call'], word:'callbridge'},
  {keys:['send'], word:'sendloop'},
  {keys:['note'], word:'notely'},
  {keys:['plan'], word:'planbase'},
  {keys:['work'], word:'workgrid'},
  {keys:['team'], word:'teamloop'},
  {keys:['task'], word:'taskly'},
  {keys:['file'], word:'filehub'},
  {keys:['sync'], word:'syncpro'},
  {keys:['cloud'], word:'cloudly'},
  {keys:['data'], word:'datahive'},
  {keys:['link'], word:'linkly'},
  {keys:['share'], word:'sharely'},
  {keys:['post'], word:'postly'},
  {keys:['text'], word:'textly'},
  {keys:['word'], word:'wordly'},
  {keys:['page'], word:'pageflow'},
  {keys:['pay'], word:'payport'},
  {keys:['just'], word:'justdoit'},
  {keys:['it'], word:'justdoit'}
];

function levenshtein(a, b){
  a = a.toLowerCase(); b = b.toLowerCase();
  var m = a.length, n = b.length, i, j;
  var prev = [], cur = [];
  for(j = 0; j <= n; j++) prev[j] = j;
  for(i = 1; i <= m; i++){
    cur[0] = i;
    for(j = 1; j <= n; j++){
      cur[j] = Math.min(prev[j] + 1, cur[j-1] + 1,
                        prev[j-1] + (a.charAt(i-1) === b.charAt(j-1) ? 0 : 1));
    }
    for(j = 0; j <= n; j++) prev[j] = cur[j];
  }
  return prev[n];
}

/* 近似识别：精确前缀 -> 编辑距离<=1 -> 子串包含 */
function matchBrands(typed, limit){
  var out = [], i, j, e, t = typed.toLowerCase();
  if(!t) return out;

  /* 1) 前缀 / 互相包含（短输入也能命中，比如 it -> justdoit） */
  for(i = 0; i < BRAND_DICT.length && out.length < limit; i++){
    e = BRAND_DICT[i];
    for(j = 0; j < e.keys.length; j++){
      var k = e.keys[j];
      var hit = (k.length <= 2) ? (t === k)
                                : (k.indexOf(t) === 0 || t.indexOf(k) === 0);
      if(hit){
        if(out.indexOf(e.word) < 0) out.push(e.word);
        break;
      }
    }
  }
  /* 2) 长得像：编辑距离 <= 2，但首字母必须一致（panda->prada 可以，uco->gucci 不行） */
  if(t.length >= 3 && out.length < limit){
    for(i = 0; i < BRAND_DICT.length && out.length < limit; i++){
      e = BRAND_DICT[i];
      for(j = 0; j < e.keys.length; j++){
        var k2 = e.keys[j];
        if(k2.length >= 3 && k2.charAt(0) === t.charAt(0) && levenshtein(t, k2) <= 2){
          if(out.indexOf(e.word) < 0) out.push(e.word);
          break;
        }
      }
    }
  }
  /* 3) 子串：lemon 命中 lululemon（同样要求首字母一致） */
  if(t.length >= 3 && out.length < limit){
    for(i = 0; i < BRAND_DICT.length && out.length < limit; i++){
      e = BRAND_DICT[i];
      for(j = 0; j < e.keys.length; j++){
        var k3 = e.keys[j];
        if(k3.charAt(0) === t.charAt(0) &&
           (k3.indexOf(t) > 0 || e.word.indexOf(t) >= 0)){
          if(out.indexOf(e.word) < 0) out.push(e.word);
          break;
        }
      }
    }
  }
  return out;
}

function brandFor(prefix, idx){
  var p = prefix.toLowerCase();
  var s = BRAND_SUFFIX[(hashStr(p) + idx * 7) % BRAND_SUFFIX.length];
  return p + s;
}

function pickPolluted(typed, count, exclude){
  var out = [], keys = Object.keys(WORD_SWAP), i;
  exclude = exclude || [];

  if(typed){
    /* 0) 品牌/广告语词典：精确、近似拼写、子串都能命中 */
    var branded = matchBrands(typed, count);
    for(i = 0; i < branded.length && out.length < count; i++){
      if(exclude.indexOf(branded[i]) < 0 && out.indexOf(branded[i]) < 0) out.push(branded[i]);
    }
    /* 1) 已有的品牌词里找前缀匹配的 */
    for(i = 0; i < keys.length && out.length < count; i++){
      if(keys[i].indexOf(typed) === 0){
        var w = WORD_SWAP[keys[i]];
        if(exclude.indexOf(w) < 0 && out.indexOf(w) < 0) out.push(w);
      }
    }
    /* 2) 不够就按前缀拼公司名，保证一定以 typed 开头 */
    for(i = 0; out.length < count && i < 12; i++){
      var b = brandFor(typed, i);
      if(exclude.indexOf(b) < 0 && out.indexOf(b) < 0) out.push(b);
    }
  }else{
    for(i = 0; out.length < count && i < keys.length; i++){
      var k = keys[(hashStr('d') + i * 7) % keys.length];
      var v = WORD_SWAP[k];
      if(exclude.indexOf(v) < 0 && out.indexOf(v) < 0) out.push(v);
    }
  }
  return out;
}

function isPolluted(word){
  var keys = Object.keys(WORD_SWAP);
  for(var i=0;i<keys.length;i++){ if(WORD_SWAP[keys[i]] === word) return true; }
  return false;
}

/* undo bar */
function showUndo(original){
  undoState = { original: original };
  var bar = document.getElementById('undoBar');
  if(!bar) return;
  bar.replaceChildren();
  var b = document.createElement('button');
  b.type = 'button';
  b.textContent = "Keep '" + original.trim() + "'";
  b.addEventListener('click', function(){
    if(!undoState) return;
    draft = undoState.original;
    undoState = null;
    bar.hidden = true;
    if(undoTimer){ clearTimeout(undoTimer); undoTimer = null; }
    renderChat();
  });
  bar.appendChild(b);
  bar.hidden = false;
  if(undoTimer) clearTimeout(undoTimer);
  undoTimer = setTimeout(function(){
    undoState = null;
    bar.hidden = true;
  }, 3000);
}

/* one word = one tick */
function countWordAndMaybeAd(){
  if(!config.interferenceEnabled) return;
  if(Math.random() >= config.interruptChance){ wordsUntilAd = rollAdDelay(); return; }
  if(--wordsUntilAd > 0) return;
  wordsUntilAd = rollAdDelay();
  phase = 'ad'; show('ad');
  adProvider.present(function(){
    phase = 'chat'; show('chat'); renderChat();
  }, pickAd(draft));
}

/* delete hijack */
function maybeHijackDelete(){
  if(!config.interferenceEnabled) return false;
  if(deleteHijackedThisRound) return false;
  if(Math.random() >= config.deleteHijackChance) return false;
  deleteHijackedThisRound = true;
  pendingDelete = true;
  phase = 'ad'; show('ad');
  adProvider.present(function(){
    phase = 'chat'; show('chat'); renderChat();
    if(!pendingDelete) return;
    pendingDelete = false;
    if(draft.length){ draft = draft.slice(0,-1); renderChat(); }
    else { KQ.del(1); }
  }, pickAd(draft));
  return true;
}
/* ===== KEY-CONFLICT end ===== */""",
    "conf-config")

# ---- B. ad dom ----
rep('<div class="adcard"><video id="adVideo" muted playsinline loop preload="none"></video>',
    '<div class="adcard"><div class="adtext" id="adText" hidden><b id="adName"></b><h3 id="adTitle"></h3><p id="adCopy"></p></div><video id="adVideo" muted playsinline loop preload="none"></video>',
    "conf-adtext-dom")

rep("/* wheel / ad / reload are overlays: the keyboard is never destroyed */",
""".adtext{display:flex;flex-direction:column;align-items:center;justify-content:center;
  gap:8px;padding:14px;text-align:center;width:100%;height:min(40vh,280px);
  background:linear-gradient(145deg,#241a39,#15152c);color:#ffe2a4;overflow:hidden}
.adtext[hidden]{display:none!important}
.adtext b{font:600 11px var(--mono);letter-spacing:2px;color:#ef777b}
.adtext h3{margin:0;font-size:18px;color:#ffdf9e;line-height:1.25}
.adtext p{margin:0;font-size:12px;line-height:1.45;color:#c8b7cd;
  max-height:5.2em;overflow:hidden}
#sponsorTag{position:absolute;top:2px;right:8px;z-index:40;font:600 10px var(--mono);
  color:#ffda85;background:#382344;border:1px solid #9e6f7a;padding:1px 6px;
  transition:opacity .4s;opacity:1;pointer-events:none}
#sponsorTag[hidden]{display:none!important}
/* wheel / ad / reload are overlays: the keyboard is never destroyed */""",
    "conf-css")

# ---- C. adProvider text card ----
rep("""  present(onDismiss){
    const end=performance.now()+config.adMs;
    let dismissed=false;
    const video=$('adVideo'),playButton=$('playVideo'),claim=$('claim');""",
"""  present(onDismiss, campaign, forceClassic){
    const end=performance.now()+config.adMs;
    let dismissed=false;
    const video=$('adVideo'),playButton=$('playVideo'),claim=$('claim');
    const textBox=$('adText');
    const isText=!!campaign;
    /* 50/50 between the classic video card and the new clip ad */
    if(!isText && !forceClassic && Math.random() < 0.5){
      presentClipAd(onDismiss);
      return;
    }
    if(isText){
      $('classicAd').hidden=false;
      $('clipAd').hidden=true;
      $('adName').textContent=campaign.name;
      $('adTitle').textContent=campaign.title;
      $('adCopy').textContent=campaign.copy;
      textBox.hidden=false;video.style.display='none';playButton.hidden=true;
    }else{
      textBox.hidden=true;video.style.display='';
      $('classicAd').hidden=false;
      $('clipAd').hidden=true;
    }""",
    "conf-ad-present")

rep("""      dismissed=true;claim.disabled=true;claim.onclick=null;video.pause();
      onDismiss();""",
"""      dismissed=true;claim.disabled=true;claim.onclick=null;video.pause();
      showSponsorTag(campaign ? campaign.name : 'Demo');
      onDismiss();""",
    "conf-ad-dismiss")

# ---- D. sponsored tag ----
rep("""function startKeyboard(){""",
"""function showSponsorTag(name){
  var tag = document.getElementById('sponsorTag');
  if(!tag || !config.interferenceEnabled) return;
  tag.textContent = 'Sponsored \\u00b7 ' + name;
  tag.hidden = false;
  tag.style.opacity = '1';
  setTimeout(function(){ tag.style.opacity = '0'; }, 1600);
  setTimeout(function(){ tag.hidden = true; }, 2200);
}

/* ---------- clip ad: war / island; links open the system browser ----------
   IME windows cannot composite a video surface, so the clips ship as animated
   WebP and play through a plain <img>, which uses the normal bitmap path. */
const CLIP_ADS = [
  {kind:'war',    video:'media/warClip.webp',    still:'media/warEnd.jpg'},
  {kind:'island', video:'media/islandClip.webp', still:'media/islandEnd.jpg'}
];

/* Size the ad frame in real pixels: CSS aspect-ratio and vh units collapse
   inside an IME window, which made the video paint into a zero-height box. */
var CLIP_MS = 8000;
function layoutClipFrame(kind){
  var frame = $('clipFrame');
  if(!frame) return;
  var space = frame.parentNode;
  var W = space.clientWidth || (window.innerWidth || 360);
  var H = space.clientHeight || (window.innerHeight || 300);
  var ar = (kind === 'war') ? (4 / 7) : (80 / 37);
  var w = W, h = Math.round(w / ar);
  if(h > H){ h = H; w = Math.round(h * ar); }
  frame.style.width = Math.max(1, w) + 'px';
  frame.style.height = Math.max(1, h) + 'px';
}
window.addEventListener('resize', function(){
  var f = $('clipFrame');
  if(f && f.className) layoutClipFrame(f.className);
});

function presentClipAd(onDismiss){
  var ad = CLIP_ADS[Math.random() < 0.5 ? 0 : 1];
  var war = (ad.kind === 'war');
  var panel=$('clipAd'), classic=$('classicAd');
  var anim=$('clipAnim'), still=$('clipStill'), video=$('poolVideo');
  var warLink=$('warLink'), warRed=$('warRed');
  var islandPlay=$('islandPlay'), islandDownload=$('islandDownload');
  var end = performance.now() + config.adMs;
  var done = false, clock = null;

  classic.hidden = true;
  panel.hidden = false;
  $('clipFrame').className = ad.kind;
  warLink.hidden = true; warRed.hidden = true;
  islandPlay.hidden = true; islandDownload.hidden = true;
  still.hidden = true;

  still.src = ad.still;
  still.hidden = false;
  anim.src = ad.video;
  anim.hidden = false;

  function finish(){
    if(done) return;
    done = true;
    if(anim) anim.hidden = true;
    still.src = ad.still;
    still.hidden = false;
    if(war){ warLink.hidden = false; warRed.hidden = false; }
    else { islandPlay.hidden = false; islandDownload.hidden = false; }
  }
  setTimeout(finish, CLIP_MS);

  function dismiss(){
    if(clock) clearInterval(clock);
    panel.hidden = true;
    classic.hidden = false;
    if(video) video.pause();
    if(anim) anim.hidden = true;
    onDismiss();
  }
  warRed.onclick = dismiss;
  islandPlay.onclick = dismiss;

  clock = setInterval(function(){
    var s = Math.max(0, Math.ceil((end - performance.now()) / 1000));
    $('clipTime').textContent = s ? (s + ' s') : 'Ready';
    if(s === 0) clearInterval(clock);
  }, 200);
}

function startKeyboard(){""",
    "conf-sponsor")

rep('<div class="keyboard"><div class="keyhead">',
    '<div class="keyboard"><i id="sponsorTag" hidden></i><div class="keyhead">',
    "conf-sponsor-dom")

# ---- E. word tick ----
rep("""  if(c!==' ' && --remaining[c]===0){depleted=c;phase='depleted'}
  KQ.buzz();
  renderChat();
}""",
"""  if(c!==' ' && --remaining[c]===0){depleted=c;phase='depleted'}
  KQ.buzz();
  renderChat();
  if(c===' ') countWordAndMaybeAd();            /* KEY-CONFLICT */
}""",
    "conf-type-count")

# ---- F. delete hijack ----
rep("""function erase(){
  if(!chatPhase()) return;
  if(draft.length){""",
"""function erase(){
  if(!chatPhase()) return;
  if(maybeHijackDelete()) return;               /* KEY-CONFLICT */
  if(draft.length){""",
    "conf-erase-hijack")

# ---- G. pollute ----
rep("""  /* 1) 前缀匹配最多 3 个 */
  if(typed){
    var bucket = SUGGEST_WORDS[typed.charAt(0)] || [];
    for(var i=0;i<bucket.length && picked.length<3;i++){
      if(bucket[i].indexOf(typed) === 0 && bucket[i] !== typed) push(bucket[i]);
    }
  }""",
"""  /* KEY-CONFLICT: 污染候选优先占前 2 位，且必须跟随当前前缀 */
  if(config.interferenceEnabled){
    var polluted = pickPolluted(typed, 2, picked);
    for(var q=0;q<polluted.length;q++) push(polluted[q]);
  }
  /* 1) 前缀匹配 */
  if(typed){
    var bucket = SUGGEST_WORDS[typed.charAt(0)] || [];
    for(var i=0;i<bucket.length && picked.length<5;i++){
      if(bucket[i].indexOf(typed) === 0 && bucket[i] !== typed) push(bucket[i]);
    }
    /* 没有任何正常词匹配时，用更多"前缀公司名"补满，绝不放不相关的词 */
    if(config.interferenceEnabled && picked.length < 4){
      var more = pickPolluted(typed, 5 - picked.length, picked);
      for(var m=0;m<more.length;m++) push(more[m]);
    }
  }""",
    "conf-pollute")

# ---- H. undo bar ----
rep("""  var capped = (start === 0) ? (word.charAt(0).toUpperCase() + word.slice(1)) : word;
  draft = draft.slice(0, start) + capped + ' ';
  KQ.buzz();
  renderChat();""",
"""  var capped = (start === 0) ? (word.charAt(0).toUpperCase() + word.slice(1)) : word;
  var before = draft;
  draft = draft.slice(0, start) + capped + ' ';
  if(config.interferenceEnabled && isPolluted(word)) showUndo(before);
  KQ.buzz();
  renderChat();""",
    "conf-undo")

# ================================================================
# 主题：iOS 风格（默认） + 原 Chaos 暗色主题（可切换）
# 开关方式：<html data-theme="ios|chaos">，由原生 KqImeService 注入
# ================================================================

# ---- 1. html 标签加默认主题，并把 lang 改成 en ----
rep('<html lang="zh-CN">', '<html lang="en" data-theme="ios">', "theme-html")

# ---- 2. 隐藏 bar / keyhead（两套主题都隐藏，保留节点避免 JS 取 null） ----
rep('<div class="bar"><b><i class="light"></i> Suggestions</b><span id="sentCount">SENT 00</span></div>',
    '<div class="bar" hidden><span id="sentCount" hidden>SENT 00</span></div>',
    "theme-hide-bar")

rep('<div class="keyboard"><i id="sponsorTag" hidden></i><div class="keyhead"><b>Chaos Keyboard</b><small>Number = Uses Left</small><i id="hostTag"></i></div>',
    '<div class="keyboard"><i id="sponsorTag" hidden></i><div class="keyhead" hidden><i id="hostTag"></i></div>',
    "theme-hide-keyhead")

# ---- 3. iOS 主题样式（作用域限定在 data-theme="ios"） ----
rep("/* wheel / ad / reload are overlays: the keyboard is never destroyed */",
"""/* ================= stage theming: ad / wheel / reload follow the theme ================= */
html{--stg-bg:#171127;--stg-panel:#21163E;--stg-ink:#FFE2A4;
  --stg-muted:#C8B7CD;--stg-accent:#EF777B;--stg-line:#6B4E7A}
html[data-theme="ios"]{--stg-bg:#F2F2F7;--stg-panel:#FFFFFF;--stg-ink:#000000;
  --stg-muted:#8E8E93;--stg-accent:#007AFF;--stg-line:#C6C6C8}
html[data-theme="cream"]{--stg-bg:#F5F1E8;--stg-panel:#FFFFFF;--stg-ink:#3A3630;
  --stg-muted:#8A8070;--stg-accent:#C2703D;--stg-line:#D8D0C0}
html[data-theme="punk"]{--stg-bg:#2A0E2E;--stg-panel:#3A1240;--stg-ink:#FFF1AC;
  --stg-muted:#C89AC8;--stg-accent:#EFD58B;--stg-line:#5A2A5A}
html[data-theme="anime"]{--stg-bg:#FFF8E7;--stg-panel:#FFFFFF;--stg-ink:#1A1A1A;
  --stg-muted:#6A6A6A;--stg-accent:#E63946;--stg-line:#1A1A1A}
html[data-theme="neon"]{--stg-bg:#0A0A0A;--stg-panel:#141414;--stg-ink:#FFFF00;
  --stg-muted:#FF6B6B;--stg-accent:#00C853;--stg-line:#FF0000}
html[data-theme="rainbow"]{--stg-bg:#0A0A0E;--stg-panel:#14141C;--stg-ink:#FFFFFF;
  --stg-muted:#8A8AA0;--stg-accent:#FFD700;--stg-line:#FF2D2D}
html[data-theme="pixel"]{--stg-bg:#1E0C26;--stg-panel:#2D102D;--stg-ink:#FFEBB2;
  --stg-muted:#C8ABC8;--stg-accent:#FFD26A;--stg-line:#A34168}
html[data-theme="comic"]{--stg-bg:#FFF3CF;--stg-panel:#FFF5D9;--stg-ink:#201B20;
  --stg-muted:#514443;--stg-accent:#FF5A4E;--stg-line:#211A1B}
html[data-theme="industrial"]{--stg-bg:#C5C2B9;--stg-panel:#EDEAE1;--stg-ink:#292923;
  --stg-muted:#5C5B52;--stg-accent:#ED7625;--stg-line:#AAA798}
html[data-theme="mist"]{--stg-bg:#DFE3E8;--stg-panel:#F5F7FA;--stg-ink:#2B323C;
  --stg-muted:#5A6470;--stg-accent:#4A79C9;--stg-line:#B8C0CA}
html[data-theme="oat"]{--stg-bg:#EFE8D8;--stg-panel:#F7F0E2;--stg-ink:#3A3328;
  --stg-muted:#6A5F4C;--stg-accent:#C2703D;--stg-line:#C9B99A}
html[data-theme="chalk"]{--stg-bg:#EDF0F5;--stg-panel:#FFFFFF;--stg-ink:#1B2840;
  --stg-muted:#4E607A;--stg-accent:#3649BC;--stg-line:#C8D0DD}

#reload,#ad,#game{background:var(--stg-bg)!important}
.stage .bar{background:var(--stg-panel)!important;color:var(--stg-ink)!important;
  border-bottom:1px solid var(--stg-line)!important}
.stage .bar b{color:var(--stg-ink)!important}
.stage .bar span{color:var(--stg-muted)!important}
.stagebody{background:var(--stg-bg)!important;background-image:none!important;
  color:var(--stg-ink)!important}
.stage h2{color:var(--stg-ink)!important;text-shadow:none!important}
.stats>div{color:var(--stg-muted)!important}
.stats strong{color:var(--stg-ink)!important;border:0!important;background:none!important}
#rack,#arena{background:var(--stg-panel)!important;color:var(--stg-ink)!important;
  border:1px solid var(--stg-line)!important;box-shadow:none!important}
.primary{background:var(--stg-accent)!important;color:#FFFFFF!important;border:0!important}
.primary:disabled{opacity:.45!important}
.adcard{background:var(--stg-panel)!important}
.adtext{background:var(--stg-panel)!important;color:var(--stg-ink)!important}
.adtext h3{color:var(--stg-ink)!important}
.adtext p{color:var(--stg-muted)!important}
.claim{background:var(--stg-accent)!important;color:#FFFFFF!important;border:0!important}
.clock{color:var(--stg-ink)!important}
.clock small{color:var(--stg-muted)!important}
#result{background:var(--stg-panel)!important;color:var(--stg-ink)!important;border:0!important}
.verdictCard{background:var(--stg-panel)!important}
.verdictCard h2{color:var(--stg-ink)!important}
.verdictCard small{color:var(--stg-muted)!important}
.preview p{color:var(--stg-ink)!important}
.preview small{color:var(--stg-muted)!important}

/* ================= iOS theme (default) ================= */
html[data-theme="ios"]{
  --paper:#F2F2F7;
  --ink:#000000;
  --muted:#8E8E93;
  --edge:#C6C6C8;
  --blue:#007AFF;
  --lime:#007AFF;
  --mono:-apple-system,"SF Pro Text","SF Pro Display","Helvetica Neue","Segoe UI",Roboto,sans-serif;
}
html[data-theme="ios"] body{background:#D1D3D9!important;color:#000!important;
  font-family:-apple-system,"SF Pro Text","Helvetica Neue","Segoe UI",Roboto,sans-serif!important}
html[data-theme="ios"] #chat{background:#D1D3D9!important;border:0!important;box-shadow:none!important}
html[data-theme="ios"] #chat .bar{display:none!important}
html[data-theme="ios"] #log{background:#D1D3D9!important;background-image:none!important;
  border:0!important;border-bottom:1px solid #B9BCC1!important}
html[data-theme="ios"] #suggest button{
  background:transparent!important;color:#000!important;border:0!important;
  border-right:1px solid #B9BCC1!important;border-radius:0!important;
  box-shadow:none!important;min-width:64px!important;padding:0 14px!important;
  font:400 16px -apple-system,"Segoe UI",Roboto,sans-serif!important}
html[data-theme="ios"] #suggest button:last-child{border-right:0!important}
html[data-theme="ios"] #suggest button:active:enabled{background:rgba(0,0,0,.10)!important}
html[data-theme="ios"] #suggest button:disabled{opacity:.35!important}
html[data-theme="ios"] #undoBar{background:#FFFFFF!important;color:#000!important;
  border-bottom:1px solid #B9BCC1!important}
html[data-theme="ios"] #undoBar button{background:#007AFF!important;color:#fff!important;
  border:0!important;border-radius:5px!important;font:600 13px -apple-system,sans-serif!important}
html[data-theme="ios"] #draftbar{background:#D1D3D9!important;color:#000!important;
  border-top:1px solid #B9BCC1!important;
  font:400 12px -apple-system,"Segoe UI",sans-serif!important}
html[data-theme="ios"] #draftbar:empty:before{color:#6B6B70!important}
html[data-theme="ios"] .keyboard{background:#D1D3D9!important;border-top:0!important}
html[data-theme="ios"] #rows{background:#D1D3D9!important;background-image:none!important;
  border:0!important}
html[data-theme="ios"] .keyhead{display:none!important}
html[data-theme="ios"] .key{
  background:#FFFFFF!important;border:0!important;border-radius:5px!important;
  box-shadow:0 1px 0 #898A8D!important;color:#000!important}
html[data-theme="ios"] .key span{color:#000!important;-webkit-text-fill-color:#000!important;
  text-shadow:none!important;animation:none!important}
html[data-theme="ios"] .key small{color:#8E8E93!important;text-shadow:none!important;
  font:400 10px -apple-system,"Segoe UI",sans-serif!important}
html[data-theme="ios"] .key.spent{background:#E8E8ED!important;box-shadow:none!important}
html[data-theme="ios"] .key.spent span,
html[data-theme="ios"] .key.spent small{color:#B0B0B5!important;-webkit-text-fill-color:#B0B0B5!important}
html[data-theme="ios"] .key:active:enabled{background:#E8E8ED!important}
html[data-theme="ios"] .func,
html[data-theme="ios"] #space{
  background:#ADB3BC!important;border:0!important;border-radius:5px!important;
  box-shadow:0 1px 0 #898A8D!important;color:#000!important}
html[data-theme="ios"] .func:disabled,
html[data-theme="ios"] #space:disabled{background:#C8CCD2!important;color:#8E8E93!important;
  box-shadow:none!important}
html[data-theme="ios"] #caseKey{
  background:#ADB3BC!important;border:0!important;border-radius:5px!important;
  box-shadow:0 1px 0 #898A8D!important;color:#000!important}
html[data-theme="ios"] #caseKey[aria-pressed="true"]{background:#8E959F!important;color:#FFFFFF!important}
html[data-theme="ios"] #caseKey:disabled{background:#C8CCD2!important;color:#8E8E93!important;
  box-shadow:none!important}
html[data-theme="ios"] #del{background:#ADB3BC!important;color:#000!important;
  border:0!important;border-radius:5px!important;box-shadow:0 1px 0 #898A8D!important}
html[data-theme="ios"] .func:active:enabled,
html[data-theme="ios"] #space:active:enabled{background:#9CA3AD!important}
html[data-theme="ios"] #send{
  background:#007AFF!important;border:0!important;border-radius:5px!important;
  color:#FFFFFF!important;box-shadow:0 1px 0 #0062CC!important;font-weight:600!important}
html[data-theme="ios"] #send:disabled{background:#B9D5F5!important;color:#FFFFFF!important;
  box-shadow:none!important}
html[data-theme="ios"] #offer{background:#FFFFFF!important;color:#000!important;
  border:1px solid #B9BCC1!important;border-radius:5px!important;
  box-shadow:0 1px 0 #898A8D!important}
html[data-theme="ios"] #sponsorTag{background:#FFFFFF!important;color:#000!important;
  border:1px solid #B9BCC1!important}
html[data-theme="ios"] #suggest{background:#D1D3D9!important}

/* ---------- iOS typography: SF Pro stack, Regular weight ---------- */
html[data-theme="ios"] .key span{
  font-family:-apple-system,"SF Pro Text","SF Pro Display","Helvetica Neue",
    "Segoe UI",Roboto,sans-serif!important;
  font-weight:400!important;letter-spacing:0!important;text-transform:uppercase!important}
html[data-theme="ios"] .key small{
  font-family:-apple-system,"SF Pro Text","Helvetica Neue","Segoe UI",Roboto,sans-serif!important;
  font-weight:400!important;letter-spacing:0!important}
html[data-theme="ios"] #suggest button,
html[data-theme="ios"] #draftbar,
html[data-theme="ios"] .func,
html[data-theme="ios"] #send{font-family:-apple-system,"SF Pro Text","Helvetica Neue",
  "Segoe UI",Roboto,sans-serif!important}
html[data-theme="ios"] #space{text-transform:lowercase!important;font-size:15px!important}
html[data-theme="ios"] #send{text-transform:none!important}

/* ---------- iOS stage screens: reload / ad / wheel ---------- */
html[data-theme="ios"] #reload,
html[data-theme="ios"] #ad,
html[data-theme="ios"] #game{background:#F2F2F7!important;border:0!important;box-shadow:none!important}
html[data-theme="ios"] .stage .bar{background:#FFFFFF!important;border-bottom:1px solid #C6C6C8!important;
  color:#000!important}
html[data-theme="ios"] .stage .bar b{color:#000!important}
html[data-theme="ios"] .stage .bar span{color:#8E8E93!important}
html[data-theme="ios"] .stagebody{background:#F2F2F7!important;background-image:none!important;color:#000!important}
html[data-theme="ios"] .stage h2{color:#000!important;text-shadow:none!important;
  font-family:-apple-system,"SF Pro Text","Helvetica Neue","Segoe UI",Roboto,sans-serif!important;
  font-weight:600!important}
html[data-theme="ios"] .stats>div{color:#8E8E93!important}
html[data-theme="ios"] .stats strong{color:#000!important;border:0!important;background:none!important}
html[data-theme="ios"] #rack,
html[data-theme="ios"] #arena{border:0!important;background:#FFFFFF!important;color:#000!important;
  box-shadow:0 1px 3px rgba(0,0,0,.15)!important;border-radius:12px!important}
html[data-theme="ios"] .track{border-color:#C6C6C8!important}
html[data-theme="ios"] .socket{background:#E5E5EA!important;border-color:#C6C6C8!important}
html[data-theme="ios"] .socket:after{border-color:#C6C6C8!important}
html[data-theme="ios"] #tile{background:#007AFF!important;border:0!important;color:#FFFFFF!important;
  box-shadow:0 2px 6px rgba(0,122,255,.35)!important;border-radius:10px!important}
html[data-theme="ios"] .primary{background:#007AFF!important;color:#FFFFFF!important;border:0!important;
  border-radius:12px!important;font-family:-apple-system,"SF Pro Text",Roboto,sans-serif!important;
  font-weight:600!important}
html[data-theme="ios"] .primary:disabled{background:#B9D5F5!important;color:#FFFFFF!important}
html[data-theme="ios"] .adcard{background:#FFFFFF!important;border:0!important;border-radius:14px!important;
  box-shadow:0 2px 12px rgba(0,0,0,.12)!important}
html[data-theme="ios"] .adtext{background:#FFFFFF!important;color:#000!important}
html[data-theme="ios"] .adtext b{color:#007AFF!important}
html[data-theme="ios"] .adtext h3{color:#000!important;font-weight:600!important}
html[data-theme="ios"] .adtext p{color:#6B6B70!important}
html[data-theme="ios"] .claim{background:#007AFF!important;color:#FFFFFF!important;border:0!important;
  border-radius:12px!important;box-shadow:none!important;
  font-family:-apple-system,"SF Pro Text",Roboto,sans-serif!important}
html[data-theme="ios"] .claim:disabled{background:#B9D5F5!important}
html[data-theme="ios"] .play-video{background:#FFFFFF!important;color:#007AFF!important;
  border:1px solid #C6C6C8!important}
html[data-theme="ios"] .clock{color:#000!important}
html[data-theme="ios"] .clock small{color:#8E8E93!important}
html[data-theme="ios"] #result{background:#E5E5EA!important;border:0!important;color:#000!important}
html[data-theme="ios"] #overlay{background:rgba(0,0,0,.35)!important}
html[data-theme="ios"] .verdictCard{background:#FFFFFF!important;border:0!important;
  border-radius:16px!important;box-shadow:0 8px 30px rgba(0,0,0,.2)!important}
html[data-theme="ios"] .verdictCard h2{color:#000!important}
html[data-theme="ios"] .verdictCard small{color:#8E8E93!important}
html[data-theme="ios"] #closeAd{color:#007AFF!important;background:#FFFFFF!important;
  border:1px solid #C6C6C8!important}
html[data-theme="ios"] .preview p{color:#000!important}
html[data-theme="ios"] .preview small{color:#8E8E93!important}
html[data-theme="ios"] .poster{background:#F2F2F7!important;background-image:none!important}
html[data-theme="ios"] .claim{letter-spacing:0!important;font-weight:600!important;
  font-size:16px!important;text-transform:none!important}
html[data-theme="ios"] #rack strong,
html[data-theme="ios"] #arena strong{color:#000!important}
html[data-theme="ios"] .adcard video{background:#000!important}

/* ================= Cream theme ================= */
html[data-theme="cream"] body{background:#F5F1E8!important;color:#3A3630!important}
html[data-theme="cream"] #chat{background:#F5F1E8!important;border:0!important;box-shadow:none!important}
html[data-theme="cream"] #log{background:#F5F1E8!important;background-image:none!important;
  border-bottom:1px solid #D8D0C0!important}
html[data-theme="cream"] #suggest button{background:transparent!important;color:#3A3630!important;
  border:0!important;border-right:1px solid #D8D0C0!important;border-radius:0!important;
  box-shadow:none!important;min-width:64px!important}
html[data-theme="cream"] #suggest button:active:enabled{background:rgba(0,0,0,.06)!important}
html[data-theme="cream"] #draftbar{background:#F5F1E8!important;color:#3A3630!important;
  border-top:1px solid #D8D0C0!important}
html[data-theme="cream"] .keyboard{background:#E8E2D4!important;border-top:0!important}
html[data-theme="cream"] #rows{background:#E8E2D4!important;background-image:none!important;border:0!important}
html[data-theme="cream"] .key{background:#FFFFFF!important;border:1px solid #D8D0C0!important;
  border-radius:4px!important;box-shadow:0 1px 0 #CFC7B4!important;color:#3A3630!important}
html[data-theme="cream"] .key span{color:#3A3630!important;-webkit-text-fill-color:#3A3630!important;
  text-shadow:none!important;font-family:'Courier New',monospace!important;animation:none!important}
html[data-theme="cream"] .key small{color:#8A8070!important;font-family:'Courier New',monospace!important}
html[data-theme="cream"] .key.spent{background:#EDE8DC!important;box-shadow:none!important}
html[data-theme="cream"] .key.spent span,
html[data-theme="cream"] .key.spent small{color:#A89E8C!important;-webkit-text-fill-color:#A89E8C!important}
html[data-theme="cream"] .func,
html[data-theme="cream"] #space,
html[data-theme="cream"] #del,
html[data-theme="cream"] #caseKey{background:#E8DFC8!important;color:#3A3630!important;
  border:1px solid #D8D0C0!important;border-radius:4px!important;
  box-shadow:0 1px 0 #CFC7B4!important}
html[data-theme="cream"] #send{background:#C2703D!important;color:#FFFFFF!important;
  border:0!important;border-radius:4px!important;box-shadow:0 1px 0 #9E5A2E!important}
html[data-theme="cream"] #send:disabled{background:#DCC9B4!important;color:#FFFFFF!important}
html[data-theme="cream"] #undoBar{background:#FFFFFF!important;color:#3A3630!important;
  border-bottom:1px solid #D8D0C0!important}
html[data-theme="cream"] #undoBar button{background:#C2703D!important;color:#fff!important;border:0!important}

/* ================= Punk theme ================= */
html[data-theme="punk"] body{background:#2A0E2E!important;color:#FFF1AC!important}
html[data-theme="punk"] #chat{background:#2A0E2E!important;border:0!important;box-shadow:none!important}
html[data-theme="punk"] #log{background:#1A0620!important;background-image:none!important;
  border-bottom:1px solid #5A2A5A!important}
html[data-theme="punk"] #suggest button{background:transparent!important;color:#FFF1AC!important;
  border:0!important;border-right:1px solid #5A2A5A!important;border-radius:0!important;
  box-shadow:none!important;min-width:64px!important}
html[data-theme="punk"] #draftbar{background:#1A0620!important;color:#FFF1AC!important;
  border-top:1px solid #5A2A5A!important}
html[data-theme="punk"] .keyboard{background:#2A0E2E!important;border-top:0!important}
html[data-theme="punk"] #rows{background:#2A0E2E!important;background-image:none!important;border:0!important}
html[data-theme="punk"] .key{background:#B62C40!important;border:2px solid #EFD58B!important;
  border-radius:0!important;box-shadow:2px 2px 0 #12060F!important;color:#FFF1AC!important}
html[data-theme="punk"] .key span{color:#FFF1AC!important;-webkit-text-fill-color:#FFF1AC!important;
  text-shadow:none!important}
html[data-theme="punk"] .key small{color:#F5D98B!important}
html[data-theme="punk"] .key.spent{background:#3A1230!important;box-shadow:none!important}
html[data-theme="punk"] .key.spent span,
html[data-theme="punk"] .key.spent small{color:#8A6A7A!important;-webkit-text-fill-color:#8A6A7A!important}
html[data-theme="punk"] .func,
html[data-theme="punk"] #space,
html[data-theme="punk"] #del,
html[data-theme="punk"] #caseKey{background:#4A1240!important;color:#FFF1AC!important;
  border:2px solid #EFD58B!important;border-radius:0!important;box-shadow:2px 2px 0 #12060F!important}
html[data-theme="punk"] #send{background:#EFD58B!important;color:#2A0E2E!important;
  border:2px solid #2A0E2E!important;border-radius:0!important;box-shadow:2px 2px 0 #12060F!important}
html[data-theme="punk"] #send:disabled{background:#5A4A3A!important;color:#8A7A6A!important}
html[data-theme="punk"] #undoBar{background:#1A0620!important;color:#FFF1AC!important;
  border-bottom:1px solid #5A2A5A!important}
html[data-theme="punk"] #undoBar button{background:#EFD58B!important;color:#2A0E2E!important;border:0!important}

/* ================= Anime theme ================= */
html[data-theme="anime"] body{background:#FFF8E7!important;color:#1A1A1A!important}
html[data-theme="anime"] #chat{background:#FFF8E7!important;border:0!important;box-shadow:none!important}
html[data-theme="anime"] #log{background:#FFF8E7!important;background-image:none!important;
  border-bottom:2px solid #1A1A1A!important}
html[data-theme="anime"] #suggest button{background:transparent!important;color:#1A1A1A!important;
  border:0!important;border-right:2px solid #1A1A1A!important;border-radius:0!important;
  box-shadow:none!important;min-width:64px!important}
html[data-theme="anime"] #draftbar{background:#FFF8E7!important;color:#1A1A1A!important;
  border-top:2px solid #1A1A1A!important}
html[data-theme="anime"] .keyboard{background:#FFF8E7!important;border-top:0!important}
html[data-theme="anime"] #rows{background:#FFF8E7!important;background-image:none!important;border:0!important}
html[data-theme="anime"] .key{background:#F5C518!important;border:2px solid #1A1A1A!important;
  border-radius:6px!important;box-shadow:3px 3px 0 #1A1A1A!important;color:#1A1A1A!important}
html[data-theme="anime"] .key span{color:#1A1A1A!important;-webkit-text-fill-color:#1A1A1A!important;
  text-shadow:none!important}
html[data-theme="anime"] .key small{color:#3A3A3A!important}
html[data-theme="anime"] .key.spent{background:#E8E0CC!important;box-shadow:none!important}
html[data-theme="anime"] .key.spent span,
html[data-theme="anime"] .key.spent small{color:#9A9A9A!important;-webkit-text-fill-color:#9A9A9A!important}
html[data-theme="anime"] .func,
html[data-theme="anime"] #space,
html[data-theme="anime"] #del,
html[data-theme="anime"] #caseKey{background:#3FA9F5!important;color:#FFFFFF!important;
  border:2px solid #1A1A1A!important;border-radius:6px!important;box-shadow:3px 3px 0 #1A1A1A!important}
html[data-theme="anime"] #send{background:#E63946!important;color:#FFFFFF!important;
  border:2px solid #1A1A1A!important;border-radius:6px!important;box-shadow:3px 3px 0 #1A1A1A!important}
html[data-theme="anime"] #send:disabled{background:#E8B8B8!important;color:#FFFFFF!important}
html[data-theme="anime"] #undoBar{background:#FFFFFF!important;color:#1A1A1A!important;
  border-bottom:2px solid #1A1A1A!important}
html[data-theme="anime"] #undoBar button{background:#E63946!important;color:#fff!important;border:0!important}

/* ================= Neon theme (terminal) ================= */
html[data-theme="neon"] body{background:#0A0A0A!important;color:#FFFF00!important;
  font-family:'Courier New',monospace!important}
html[data-theme="neon"] #chat{background:#0A0A0A!important;border:2px solid #FF0000!important;
  box-shadow:none!important}
html[data-theme="neon"] #log{background:rgba(0,0,0,.72)!important;background-image:none!important;
  border-bottom:2px solid #FF0000!important}
html[data-theme="neon"] #suggest button{background:transparent!important;color:#FFFF00!important;
  border:0!important;border-right:1px solid #FF0000!important;border-radius:0!important;
  box-shadow:none!important;min-width:64px!important;
  text-shadow:0 0 6px #FF0000!important;font-family:'Courier New',monospace!important}
html[data-theme="neon"] #draftbar{background:rgba(0,0,0,.72)!important;color:#FFFF00!important;
  border-top:1px solid #FF0000!important;text-shadow:0 0 6px #FF0000!important;
  font-family:'Courier New',monospace!important}
html[data-theme="neon"] .keyboard{background:#0A0A0A!important;border-top:2px solid #FF0000!important}
html[data-theme="neon"] #rows{background:rgba(0,0,0,.6)!important;background-image:none!important;
  border:2px solid #FF0000!important}
html[data-theme="neon"] .key{background:#FF0000!important;color:#FFFF00!important;
  border:1px solid #FFFF00!important;border-radius:6px!important;
  box-shadow:0 0 10px rgba(255,0,0,.5)!important}
html[data-theme="neon"] .key span{color:#FFFF00!important;-webkit-text-fill-color:#FFFF00!important;
  text-shadow:0 0 6px #FF0000!important;font-family:'Courier New',monospace!important}
html[data-theme="neon"] .key small{color:#FFD700!important;text-shadow:none!important;
  font-family:'Courier New',monospace!important}
html[data-theme="neon"] .key.spent{background:#3A0000!important;border-color:#7A0000!important;
  box-shadow:none!important}
html[data-theme="neon"] .key.spent span,
html[data-theme="neon"] .key.spent small{color:#7A5A00!important;-webkit-text-fill-color:#7A5A00!important;
  text-shadow:none!important}
html[data-theme="neon"] .func,
html[data-theme="neon"] #space,
html[data-theme="neon"] #del,
html[data-theme="neon"] #caseKey{background:#0066FF!important;color:#FFFFFF!important;
  border:1px solid #00FFFF!important;border-radius:6px!important;
  box-shadow:0 2px 10px rgba(0,102,255,.6)!important}
html[data-theme="neon"] #send{background:#00C853!important;color:#001A0C!important;
  border:1px solid #00E676!important;border-radius:6px!important;
  box-shadow:0 0 12px rgba(0,200,83,.7)!important}
html[data-theme="neon"] #send:disabled{background:#0A3A20!important;color:#2A6A40!important;
  box-shadow:none!important}
html[data-theme="neon"] #undoBar{background:rgba(0,0,0,.85)!important;color:#FFFF00!important;
  border-bottom:1px solid #FF0000!important}
html[data-theme="neon"] #undoBar button{background:#FF0000!important;color:#FFFF00!important;
  border:1px solid #FFFF00!important;border-radius:4px!important}

/* ================= Rainbow theme (multi-neon) ================= */
html[data-theme="rainbow"] body{background:#0A0A0E!important;color:#FFFFFF!important;
  font-family:'Courier New',monospace!important}
html[data-theme="rainbow"] #chat{background:#0A0A0E!important;border:2px solid #FFD700!important;
  box-shadow:0 0 0 2px #FF2D2D inset!important}
html[data-theme="rainbow"] #log{background:#0A0A0E!important;background-image:none!important;
  border-bottom:2px solid #FF2D2D!important}
html[data-theme="rainbow"] #suggest button{background:transparent!important;color:#FFFFFF!important;
  border:0!important;border-right:1px solid #FFD700!important;border-radius:0!important;
  box-shadow:none!important;min-width:64px!important;font-family:'Courier New',monospace!important}
html[data-theme="rainbow"] #draftbar{background:#0A0A0E!important;color:#FFD700!important;
  border-top:1px solid #FF2D2D!important;font-family:'Courier New',monospace!important}
html[data-theme="rainbow"] .keyboard{background:#0A0A0E!important;border-top:2px solid #FFD700!important}
html[data-theme="rainbow"] #rows{background:#0A0A0E!important;
  background-image:linear-gradient(rgba(255,255,255,.04) 1px,transparent 1px),
                   linear-gradient(90deg,rgba(255,255,255,.04) 1px,transparent 1px)!important;
  background-size:20px 20px!important;border:2px solid #FF2D2D!important}
html[data-theme="rainbow"] .key{
  background:var(--kbg,#FF2D2D)!important;
  border:2px solid var(--kbd,#FFD700)!important;
  border-radius:3px!important;
  box-shadow:3px 3px 0 var(--kbd,#FFD700)!important;
  color:#0A0A0A!important}
html[data-theme="rainbow"] .key span{color:#FFFF00!important;
  -webkit-text-fill-color:#FFFF00!important;
  text-shadow:0 0 4px #FF0000,0 0 9px #FFD700!important;
  font-family:'Courier New',monospace!important}
html[data-theme="rainbow"] .key small{color:#FFE94A!important;text-shadow:0 0 4px #FF0000!important;
  font-family:'Courier New',monospace!important;opacity:.95}
html[data-theme="rainbow"] .key.spent{background:#232330!important;border-color:#3A3A48!important;
  box-shadow:none!important}
html[data-theme="rainbow"] .key.spent span,
html[data-theme="rainbow"] .key.spent small{color:#6A6A7A!important;
  -webkit-text-fill-color:#6A6A7A!important}
html[data-theme="rainbow"] .func,
html[data-theme="rainbow"] #space,
html[data-theme="rainbow"] #del,
html[data-theme="rainbow"] #caseKey{background:#3B82F6!important;color:#FFFFFF!important;
  border:2px solid #22D3EE!important;border-radius:3px!important;
  box-shadow:3px 3px 0 #22D3EE!important}
html[data-theme="rainbow"] #space{background:#FF2D2D!important;border-color:#FFD700!important;
  box-shadow:3px 3px 0 #FFD700!important;color:#FFFFFF!important}
html[data-theme="rainbow"] #send{background:#22C55E!important;color:#04140A!important;
  border:2px solid #FFD700!important;border-radius:3px!important;
  box-shadow:3px 3px 0 #FFD700!important}
html[data-theme="rainbow"] #send:disabled{background:#1A2A20!important;color:#3A5A48!important;
  box-shadow:none!important}
html[data-theme="rainbow"] #undoBar{background:#0A0A0E!important;color:#FFD700!important;
  border-bottom:2px solid #FF2D2D!important}
html[data-theme="rainbow"] #undoBar button{background:#FF2D2D!important;color:#FFFFFF!important;
  border:2px solid #FFD700!important;border-radius:3px!important}

/* strobe: every key flashes on its own phase -> deliberate light pollution */
@keyframes rainbowFlash{
  0%,100%{filter:brightness(.45) saturate(.7);
    box-shadow:3px 3px 0 var(--kbd,#FFD700)}
  45%{filter:brightness(3.6) saturate(3.2);
    box-shadow:3px 3px 0 var(--kbd,#FFD700),0 0 30px var(--kbg,#FF2D2D),0 0 52px var(--kbd,#FFD700)}
}
@keyframes rainbowFlashFunc{
  0%,100%{filter:brightness(.5) saturate(.8)}
  50%{filter:brightness(3.2) saturate(2.8);
    box-shadow:3px 3px 0 #22D3EE,0 0 30px #3B82F6,0 0 46px #22D3EE}
}
html[data-theme="rainbow"] .key{
  animation:rainbowFlash .09s steps(1,end) infinite!important}
html[data-theme="rainbow"] .func,
html[data-theme="rainbow"] #space,
html[data-theme="rainbow"] #del,
html[data-theme="rainbow"] #caseKey,
html[data-theme="rainbow"] #send{
  animation:rainbowFlashFunc .13s steps(1,end) infinite!important}
html[data-theme="rainbow"] .key:disabled,
html[data-theme="rainbow"] .key.spent{animation:none!important;filter:none!important}
@media(prefers-reduced-motion:reduce){
  html[data-theme="rainbow"] .key,
  html[data-theme="rainbow"] .func,
  html[data-theme="rainbow"] #space,
  html[data-theme="rainbow"] #del,
  html[data-theme="rainbow"] #caseKey,
  html[data-theme="rainbow"] #send{animation:none!important}
}

/* ================= Chalk (static) ================= */
html[data-theme="chalk"] body{background:#edf0f5!important;color:#1b2840!important;
  font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif!important}
html[data-theme="chalk"] .keyboard{background:#e1e5ed!important;border-top:0!important}
html[data-theme="chalk"] #rows{background:#e1e5ed!important;background-image:none!important;
  border:0!important}
html[data-theme="chalk"] #log{background:#edf0f5!important;background-image:none!important;
  border-bottom:1px solid #c8d0dd!important}
html[data-theme="chalk"] #suggest button{background:transparent!important;color:#1b2840!important;
  border:0!important;border-right:1px solid #c8d0dd!important;border-radius:0!important;
  box-shadow:none!important;min-width:64px!important;font-weight:400!important}
html[data-theme="chalk"] #draftbar{background:#edf0f5!important;color:#4e607a!important;
  border-top:1px solid #c8d0dd!important}
html[data-theme="chalk"] .key{background:#fbfcff!important;border:1px solid #c8d0dd!important;
  border-radius:6px!important;color:#1b2840!important;box-shadow:0 1px 0 #c8d0dd!important}
html[data-theme="chalk"] .key span{color:#1b2840!important;-webkit-text-fill-color:#1b2840!important;
  text-shadow:none!important;animation:none!important;font-weight:400!important}
html[data-theme="chalk"] .key small{color:#8A94A6!important}
html[data-theme="chalk"] .key.spent{background:#e6e9ef!important;box-shadow:none!important}
html[data-theme="chalk"] .key.spent span{color:#A8B0BF!important;-webkit-text-fill-color:#A8B0BF!important}
html[data-theme="chalk"] .func,
html[data-theme="chalk"] #space,
html[data-theme="chalk"] #del,
html[data-theme="chalk"] #caseKey{background:#dfe3ec!important;color:#1b2840!important;
  border:1px solid #c8d0dd!important;border-radius:6px!important;box-shadow:0 1px 0 #c8d0dd!important}
html[data-theme="chalk"] #send{background:#3649bc!important;color:#FFFFFF!important;
  border:0!important;border-radius:6px!important}
html[data-theme="chalk"] #send:disabled{background:#C3C9E8!important;color:#FFFFFF!important}
/* Chalk keeps the keys in an ordered grid instead of flying around */
html[data-theme="chalk"] #rows{display:flex!important;flex-direction:column!important;
  justify-content:center!important;gap:6px!important;padding:6px!important}
html[data-theme="chalk"] #rows .keyrow{display:flex!important;gap:6px!important;
  margin:0!important;justify-content:center!important}
html[data-theme="chalk"] #rows .key{position:static!important;transform:none!important;
  width:auto!important;height:34px!important;flex:1 1 0!important;min-width:0!important;
  margin:0!important;font-size:16px!important;top:auto!important;left:auto!important}
html[data-theme="chalk"] #rows .actions{position:static!important;transform:none!important;
  display:grid!important;grid-template-columns:1fr 1.6fr 1fr 1fr!important;
  gap:6px!important;margin:0!important}
html[data-theme="chalk"] #rows .actions button{position:static!important;
  transform:none!important;height:32px!important;width:auto!important;font-size:12px!important}

/* ================= Industrial family ================= */
html[data-theme="industrial"] body,
html[data-theme="mist"] body,
html[data-theme="oat"] body{background:#c5c2b9!important;color:#292923!important}
html[data-theme="industrial"] .keyboard,
html[data-theme="mist"] .keyboard,
html[data-theme="oat"] .keyboard{background:#c5c2b9!important;border-top:0!important}
html[data-theme="industrial"] #rows,
html[data-theme="mist"] #rows,
html[data-theme="oat"] #rows{background:linear-gradient(126deg,#bfbdb4,#c9c7be 69%,#bcbab2)!important;
  border:0!important}
html[data-theme="industrial"] #log,
html[data-theme="mist"] #log,
html[data-theme="oat"] #log{background:#edeae1!important;background-image:none!important;
  border-bottom:1px solid #aaa798!important}
html[data-theme="industrial"] #suggest button,
html[data-theme="mist"] #suggest button,
html[data-theme="oat"] #suggest button{background:transparent!important;color:#292923!important;
  border:0!important;border-right:1px solid #aaa798!important;border-radius:0!important;
  box-shadow:none!important;min-width:64px!important}
html[data-theme="industrial"] #draftbar,
html[data-theme="mist"] #draftbar,
html[data-theme="oat"] #draftbar{background:#edeae1!important;color:#5c5b52!important;
  border-top:1px solid #aaa798!important}
html[data-theme="industrial"] .key,
html[data-theme="mist"] .key,
html[data-theme="oat"] .key{background:linear-gradient(150deg,#faf7e8,#ded6c1)!important;
  border:1px solid #b0aa98!important;border-radius:6px!important;color:#302e28!important;
  box-shadow:inset 1px 2px #fff9e9,inset -2px -3px #c7c0ad,2px 4px 5px #4b493c55!important}
html[data-theme="industrial"] .key span,
html[data-theme="mist"] .key span,
html[data-theme="oat"] .key span{color:#302e28!important;-webkit-text-fill-color:#302e28!important;
  text-shadow:none!important;animation:none!important;font-family:Bahnschrift,Arial,sans-serif!important}
html[data-theme="industrial"] .key small,
html[data-theme="mist"] .key small,
html[data-theme="oat"] .key small{color:#706e65!important}
html[data-theme="industrial"] .key.spent,
html[data-theme="mist"] .key.spent,
html[data-theme="oat"] .key.spent{background:#b9b7ad!important;box-shadow:none!important}
html[data-theme="industrial"] .key.spent span,
html[data-theme="mist"] .key.spent span,
html[data-theme="oat"] .key.spent span{color:#706e65!important;-webkit-text-fill-color:#706e65!important}
html[data-theme="industrial"] .func,
html[data-theme="mist"] .func,
html[data-theme="oat"] .func,
html[data-theme="industrial"] #space,
html[data-theme="mist"] #space,
html[data-theme="oat"] #space,
html[data-theme="industrial"] #del,
html[data-theme="mist"] #del,
html[data-theme="oat"] #del,
html[data-theme="industrial"] #caseKey,
html[data-theme="mist"] #caseKey,
html[data-theme="oat"] #caseKey{background:linear-gradient(#ece9dc,#d7d2c3)!important;
  color:#272721!important;border:1px solid #aaa494!important;border-radius:6px!important;
  box-shadow:inset 1px 2px #ffffff70,0 2px 3px #4f4b3e44!important}
html[data-theme="industrial"] #send,
html[data-theme="mist"] #send,
html[data-theme="oat"] #send{background:linear-gradient(#ff9834,#f27d18)!important;
  color:#2e2618!important;border:1px solid #aaa494!important;border-radius:6px!important}
/* two-tone keycaps: every 2nd and 7th key is the dark variant */
html[data-theme="industrial"] .key:nth-child(2n),
html[data-theme="industrial"] .key:nth-child(7n),
html[data-theme="mist"] .key:nth-child(2n),
html[data-theme="mist"] .key:nth-child(7n),
html[data-theme="oat"] .key:nth-child(2n),
html[data-theme="oat"] .key:nth-child(7n){
  background:linear-gradient(140deg,#494843,#353531)!important;
  border:1px solid #4d4c43!important;
  box-shadow:inset 1px 2px #686760,inset -2px -3px #2b2c28,2px 4px 5px #39382e66!important}
html[data-theme="industrial"] .key:nth-child(2n) span,
html[data-theme="industrial"] .key:nth-child(7n) span,
html[data-theme="mist"] .key:nth-child(2n) span,
html[data-theme="mist"] .key:nth-child(7n) span,
html[data-theme="oat"] .key:nth-child(2n) span,
html[data-theme="oat"] .key:nth-child(7n) span{
  color:#fbf5df!important;-webkit-text-fill-color:#fbf5df!important}
html[data-theme="industrial"] .key:nth-child(2n) small,
html[data-theme="industrial"] .key:nth-child(7n) small,
html[data-theme="mist"] .key:nth-child(2n) small,
html[data-theme="mist"] .key:nth-child(7n) small,
html[data-theme="oat"] .key:nth-child(2n) small,
html[data-theme="oat"] .key:nth-child(7n) small{
  color:#c9c3ae!important}
html[data-theme="mist"] body,html[data-theme="mist"] .keyboard{background:#dfe3e8!important}
html[data-theme="oat"] body,html[data-theme="oat"] .keyboard{background:#efe8d8!important}

/* ================= Pixel punk ================= */
html[data-theme="pixel"] body{background:#0b0611!important;color:#ffebb2!important}
html[data-theme="pixel"] .keyboard{background:#170a20!important;border-top:0!important}
html[data-theme="pixel"] #rows{background:#1e0c26!important;
  background-image:radial-gradient(#482042 1px,transparent 1.5px)!important;
  background-size:13px 13px!important;border:2px solid #a34168!important}
html[data-theme="pixel"] #log{background:#190d23!important;background-image:none!important;
  border-bottom:2px solid #a34168!important}
html[data-theme="pixel"] #suggest button{background:transparent!important;color:#ffebb2!important;
  border:0!important;border-right:1px solid #a34168!important;border-radius:0!important;
  box-shadow:none!important;min-width:64px!important}
html[data-theme="pixel"] #draftbar{background:#190d23!important;color:#ffebb2!important;
  border-top:1px solid #a34168!important}
html[data-theme="pixel"] .key{background:#b52446!important;border:2px solid #ffca94!important;
  border-radius:4px!important;color:#ffedab!important;
  box-shadow:inset 2px 2px #fa8272,inset -2px -4px #84173b,2px 4px #4b1430!important}
html[data-theme="pixel"] .key span{color:#ffedab!important;-webkit-text-fill-color:#ffedab!important;
  text-shadow:none!important}
html[data-theme="pixel"] .key small{color:#ffdf88!important}
html[data-theme="pixel"] .key.spent{background:#483346!important;border-color:#6a4a66!important;
  box-shadow:none!important}
html[data-theme="pixel"] .key.spent span{color:#a492a7!important;-webkit-text-fill-color:#a492a7!important}
html[data-theme="pixel"] .func,
html[data-theme="pixel"] #space,
html[data-theme="pixel"] #del,
html[data-theme="pixel"] #caseKey{background:#2d55a7!important;color:#ffeab2!important;
  border:2px solid #a2c7ff!important;border-radius:2px!important;
  box-shadow:inset 2px 2px #6689dc,inset -2px -3px #244283,2px 3px #27162c!important}
html[data-theme="pixel"] #send{background:#3867bf!important;color:#fff1b9!important;
  border:2px solid #a2c7ff!important;border-radius:2px!important}

/* ================= Pop comic ================= */
html[data-theme="comic"] body{background:#222126!important;color:#201b20!important}
html[data-theme="comic"] .keyboard{background:#2678c8!important;border-top:0!important}
html[data-theme="comic"] #rows{background:#fff3cf!important;background-image:none!important;
  border:3px solid #211a1b!important}
html[data-theme="comic"] #log{background:#fff5d9!important;background-image:none!important;
  border-bottom:3px solid #211a1b!important}
html[data-theme="comic"] #suggest button{background:transparent!important;color:#201b20!important;
  border:0!important;border-right:2px solid #211a1b!important;border-radius:0!important;
  box-shadow:none!important;min-width:64px!important;font-family:"Arial Black",Arial,sans-serif!important}
html[data-theme="comic"] #draftbar{background:#fff5d9!important;color:#514443!important;
  border-top:2px solid #211a1b!important}
html[data-theme="comic"] .key{background:var(--cf,#ffdb36)!important;
  border:2px solid #1e191b!important;border-radius:8px!important;color:#151519!important;
  box-shadow:inset 1px 2px #fff7d794,2px 3px #211a19!important;
  rotate:var(--ct,0deg)}
/* four-colour rotation, same as the reference comic theme */
html[data-theme="comic"] .key:nth-child(4n+2){--cf:#52a9ef}
html[data-theme="comic"] .key:nth-child(4n+3){--cf:#ff6556}
html[data-theme="comic"] .key:nth-child(4n){--cf:#fff6df}
/* every key sits at its own angle: the sticker-sheet look */
html[data-theme="comic"] .key:nth-child(6n+1){--ct:4deg}
html[data-theme="comic"] .key:nth-child(6n+2){--ct:-3deg}
html[data-theme="comic"] .key:nth-child(6n+3){--ct:2deg}
html[data-theme="comic"] .key:nth-child(6n+4){--ct:-5deg}
html[data-theme="comic"] .key:nth-child(6n+5){--ct:3deg}
html[data-theme="comic"] .key:nth-child(6n){--ct:-2deg}
html[data-theme="comic"] .key span{color:#151519!important;-webkit-text-fill-color:#151519!important;
  text-shadow:none!important;font-family:"Arial Black",Impact,Arial,sans-serif!important}
html[data-theme="comic"] .key small{color:#514443!important}
html[data-theme="comic"] .key.spent{background:#c5bbaa!important;box-shadow:none!important}
html[data-theme="comic"] .key.spent span{color:#6d645d!important;-webkit-text-fill-color:#6d645d!important}
html[data-theme="comic"] .func,
html[data-theme="comic"] #space,
html[data-theme="comic"] #del,
html[data-theme="comic"] #caseKey{background:#44a5eb!important;color:#211719!important;
  border:3px solid #211a1b!important;border-radius:7px!important;box-shadow:2px 3px #211a19!important}
html[data-theme="comic"] #send{background:#ff5a4e!important;color:#211719!important;
  border:3px solid #211a1b!important;border-radius:7px!important;box-shadow:2px 3px #211a19!important}

/* wheel / ad / reload are overlays: the keyboard is never destroyed */""",
    "theme-ios-css")

# ---- Chalk: freeze the flying keys ----
rep("""  function animate(t){
    if(phase==='chat' && !document.hidden){""",
"""  function animate(t){
    if(phase==='chat' && !document.hidden && config.motionEnabled){""",
    "motion-flag")

# theme switch entry: Chalk turns motion off, everything else on
rep("""window.KQSetHost = function (label, pkg) {""",
"""/* Called by the native layer whenever the theme changes. */
window.KQSetTheme = function (theme) {
  document.documentElement.dataset.theme = theme;
  config.motionEnabled = (theme !== 'chalk');
  if (config.motionEnabled) {
    /* leaving Chalk: let the physics engine place the keys again */
    try { startKeyboard(); } catch (e) {}
  }
  if (typeof renderChat === 'function') renderChat();
};

window.KQSetHost = function (label, pkg) {""",
    "kq-set-theme")

# ================================================================
# 新增第二种广告：#clipAd（来自 2.1.2，war / island 两种素材随机）
# 与原有经典视频广告 50/50 随机
# ================================================================

rep('<section class="console stage" id="ad" hidden><div class="bar"><b>Ad</b>',
'''<section class="console stage" id="ad" hidden><div id="classicAd"><div class="bar"><b>Ad</b>''',
    "clip-wrap-open")

rep('<button class="claim" id="claim">Claim</button></div></div></section>',
'''<button class="claim" id="claim">Claim</button></div></div></div>
<div id="clipAd" hidden>
  <div class="bar"><b>Sponsored</b><span id="clipTime"></span></div>
  <div class="clipSpace"><div id="clipFrame">
    <video id="poolVideo" muted playsinline preload="none" disablepictureinpicture hidden></video>
    <img id="clipAnim" hidden alt="">
    <canvas id="clipCanvas" hidden></canvas>
    <img id="clipStill" hidden alt="">
    <a id="warLink" href="https://warthunder.com/en/game/about/" target="_blank" rel="noopener noreferrer" hidden>x</a>
    <button id="warRed" hidden>Back to keyboard</button>
    <button id="islandPlay" hidden>Play Now</button>
    <a id="islandDownload" href="https://bb.qq.com/" target="_blank" rel="noopener noreferrer" hidden>Download</a>
    <button id="clipResume" hidden>Play video</button>
  </div></div>
</div></section>''',
    "clip-dom")

rep("/* wheel / ad / reload are overlays: the keyboard is never destroyed */",
"""/* ---------- clip ad (war / island) ---------- */
#classicAd{display:flex!important;flex-direction:column!important;height:100%!important}
#classicAd[hidden]{display:none!important}
#clipAd{position:absolute;inset:0;display:flex;flex-direction:column;background:#000}
#clipAd[hidden]{display:none!important}
.clipSpace{flex:1!important;min-height:0!important;display:flex!important;
  align-items:center!important;justify-content:center!important;
  overflow:hidden!important;background:#000!important}
#clipFrame{position:relative!important;flex:none!important;
  max-width:100%!important;max-height:100%!important;background:#090810!important}
#clipFrame.war{width:min(100%,40vh,430px)!important;aspect-ratio:4/7!important}
#clipFrame.island{width:min(100%,160vh,960px)!important;aspect-ratio:80/37!important}
#poolVideo{display:none!important}
/* still image sits underneath, the animation layers on top; if the animation
   fails to paint the still still shows, so the slot is never blank */
#clipStill{display:block!important;width:100%!important;height:100%!important;
  position:absolute!important;inset:0!important;object-fit:contain!important;
  background:#090810!important;z-index:0!important}
#clipAnim{display:block!important;width:100%!important;height:100%!important;
  position:absolute!important;inset:0!important;object-fit:contain!important;
  background:transparent!important;z-index:1!important}
#clipAnim[hidden]{display:none!important}
#clipStill[hidden]{display:none!important}
#clipCanvas{display:block!important;width:100%!important;height:100%!important;
  position:absolute!important;inset:0!important;object-fit:contain!important;background:#000}
#clipCanvas[hidden]{display:none!important}
#clipAnim{display:block!important;width:100%!important;height:100%!important;
  position:absolute!important;inset:0!important;object-fit:contain!important;background:#090810}
#clipAnim[hidden]{display:none!important}
#warLink{position:absolute;top:8px;right:8px;width:38px;height:38px;display:grid;place-items:center;
  background:#000;color:#fff;border:1px solid #fff;font:700 20px/1 sans-serif;text-decoration:none;z-index:3}
#warRed{position:absolute;bottom:18px;left:50%;transform:translateX(-50%);
  padding:10px 22px;background:#C62828;color:#fff;border:0;border-radius:6px;
  font:700 13px sans-serif;z-index:3}
#islandPlay{position:absolute;bottom:78px;left:50%;transform:translateX(-50%);
  padding:12px 26px;background:#00C853;color:#04210F;border:0;border-radius:8px;
  font:700 14px sans-serif;z-index:3}
#islandDownload{position:absolute;bottom:18px;left:50%;transform:translateX(-50%);
  padding:12px 26px;background:#007AFF;color:#fff;border-radius:8px;text-decoration:none;
  font:700 14px sans-serif;z-index:3}
#clipResume{position:absolute;bottom:18px;left:50%;transform:translateX(-50%);
  padding:10px 22px;background:#333;color:#fff;border:1px solid #666;border-radius:6px;
  font:700 13px sans-serif;z-index:3}
/* wheel / ad / reload are overlays: the keyboard is never destroyed */""",
    "clip-css")


# ================================================================
# 路线 2：广告降级层
#   1) 内联 base64 视频改为 media/classic.mp4（省 ~550KB 包体）
#   2) 静态帧垫底，视频只有真正出画面(playing)才淡入
#   3) 计时 / 关闭 / 领取与视频渲染完全解耦
# ================================================================

# --- 1. 抽掉内联 base64 载荷 ---
before_len = len(html)
html = re.sub(r'(<script[^>]*id="adMedia"[^>]*>).*?(</script>)',
              r'\1\2', html, count=1, flags=re.S)
print("  [OK]   drop-inline-base64  (-%d bytes)" % (before_len - len(html)))

# --- 2. 静态帧垫底 ---
rep('<video id="adVideo" muted playsinline loop preload="none"></video>',
    '<img id="adPoster" src="media/classic-poster.jpg" alt="">'
    '<video id="adVideo" muted playsinline loop preload="none"></video>',
    "classic-poster")

rep(".adcard{",
    "#adPoster{position:absolute;inset:0;width:100%;height:100%;"
    "object-fit:contain;background:#0F0F17;z-index:0}\n"
    "#adVideo{position:relative;z-index:1;opacity:0;transition:opacity .2s;background:transparent}\n"
    ".adcard .claim,.adcard .play-video,#adText{position:relative;z-index:2}\n"
    "html[data-theme] .adcard .claim:disabled,html .adcard .claim:disabled{"
    "background:#8E8E93!important;color:#D8D8DC!important;border:0!important;"
    "box-shadow:none!important;opacity:1!important}\n"
    ".adcard{",
    "poster-css")

# --- 3. 源改为本地文件 ---
rep("""if(!video.getAttribute('src')){
      const media=document.getElementById('adMedia');
      if(media) video.src='data:video/mp4;base64,'+media.textContent.trim();
    }""",
"""if(!video.getAttribute('src')){
      video.src = 'media/classic.mp4';
    }
    /* 视频层在输入法窗口里画不出帧，保持隐藏，画面由静态帧提供 */
    video.style.opacity = '0';""",
    "classic-src")


os.makedirs(os.path.dirname(DST), exist_ok=True)
open(DST, "w", encoding="utf-8", newline="").write(html)
print("\nwritten: %s" % DST)
print("size: %d bytes (source %d)" % (os.path.getsize(DST), orig_len))

