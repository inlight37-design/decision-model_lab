/* island-ui motion.js — 그대로 붙여 쓴다. 함수는 고치지 말고 부르기만 한다.
   근거: 애플 WWDC18·23·25(research/MOTION.md). 값: 사용자가 나란히 눌러 보고 고른 '애플식 3번'. */

// 탄력. frequent = 자주 누르는 것(누른 뒤 돌아오기·선택 표시·접기), rare = 가끔 여는 것(버튼 → 패널).
// response = 한 번 출렁이는 주기(초, 애플의 duration), damping 1 = 튕김 없음(애플 bounce = 1 − damping)
const FEEL = { frequent: { response: 0.4, damping: 0.85 }, rare: { response: 0.42, damping: 0.66 } };

// 스프링 하나 = 움직이는 값 하나. 요소마다 한 번 만들고 입력이 올 때마다 to()로 목표만 바꾼다.
// 지금 값과 속도를 이어받으므로 도중에 다시 눌러도 튀지 않는다.
function createSpring(value, onUpdate) {
  let x = value, v = 0, target = value, k = 0, c = 0, eps = 0.0005, last = 0, raf = 0, onRest = null;
  const tick = now => {
    const dt = Math.max(0, Math.min(0.05, (now - last) / 1000)); last = now;
    const n = Math.max(1, Math.ceil(dt / 0.004)), h = dt / n;   // 4ms씩 나눠 적분(반-암시적 오일러)
    for (let i = 0; i < n; i++) { v += (-k * (x - target) - c * v) * h; x += v * h; }
    if (Math.abs(v) < eps * 10 && Math.abs(x - target) < eps) {
      x = target; v = 0; raf = 0; onUpdate(x);
      const done = onRest; onRest = null; if (done) done();
      return;
    }
    onUpdate(x); raf = requestAnimationFrame(tick);
  };
  const api = {
    get value() { return x; }, get velocity() { return v; }, get target() { return target; },
    get moving() { return raf !== 0; },
    to(next, { response = FEEL.rare.response, damping = FEEL.rare.damping, velocity, precision, onRest: done } = {}) {
      if (matchMedia('(prefers-reduced-motion: reduce)').matches) return api.jump(next, done);
      if (velocity !== undefined) v = velocity;
      eps = precision ?? Math.max(0.0005, Math.abs(next - x) * 0.001);   // 멈췄다고 볼 거리. 기본은 움직일 거리의 0.1%
      target = next; onRest = done || null;
      const w = 2 * Math.PI / response; k = w * w; c = 2 * damping * w;
      if (!raf) { last = performance.now(); raf = requestAnimationFrame(tick); }
      return api;
    },
    jump(next, done) { api.stop(); x = target = next; v = 0; onUpdate(x); if (done) done(); return api; },
    stop() { if (raf) cancelAnimationFrame(raf); raf = 0; return api; },
  };
  return api;
}

// 누름: 누르는 순간 요소 크기에 맞춰 조금 줄고(SEED 공식: 가로로 최대 약 8px), 떼면 탄력 있게 돌아온다.
// 누르지 않았으면(마우스를 올렸다 떼기만 하면) 움직이지 않는다. tint: true면 누르는 동안 .is-pressed(눌림 색).
function attachPress(el, { tint = true } = {}) {
  if (el._press) return;
  const s = el._press = createSpring(1, v => { el.style.transform = Math.abs(v - 1) < 1e-4 ? '' : `scale(${v})`; });
  let pressed = false;
  el.addEventListener('pointerdown', () => {
    if (el.disabled || el.getAttribute('aria-disabled') === 'true') return;
    pressed = true;
    const r = el.getBoundingClientRect(), k = s.value || 1;
    const basis = Math.max(r.height / k, r.width / k / 4, 24);
    s.to((basis - 2) / basis, { response: 0.18, damping: 1 });
    if (tint) el.classList.add('is-pressed');
  });
  const up = () => {
    if (!pressed) return;
    pressed = false;
    s.to(1, FEEL.frequent);
    if (tint) el.classList.remove('is-pressed');
  };
  ['pointerup', 'pointerleave', 'pointercancel'].forEach(t => el.addEventListener(t, up));
}

// 접기·펼치기: box의 첫 자식이 내용이다. 도중에 반대로 눌러도 지금 높이·속도에서 이어지고, 닫을 때는 튕기지 않는다.
// box는 CSS에서 overflow: hidden, 닫힌 상태 height: 0으로 둔다.
function animateHeight(box, open) {
  const inner = box.firstElementChild;
  if (!inner) return;
  box.style.overflow = 'hidden';
  const s = box._height || (box._height = createSpring(0, v => { box.style.height = Math.max(0, v) + 'px'; }));
  if (!s.moving) s.jump(box.getBoundingClientRect().height);   // 멈춰 있던 사이 내용이 바뀌었을 수 있다
  s.to(open ? inner.getBoundingClientRect().height : 0, {
    response: FEEL.frequent.response, damping: open ? FEEL.frequent.damping : 1,
    onRest: () => { box.style.height = open ? 'auto' : '0px'; },
  });
}

// 선택 표시: 구간 선택·탭 막대(bar)의 .seg-indicator가 고른 항목으로 옮겨 간다. 앞쪽 끝은 빨리, 뒤쪽 끝은 늦게 따라와
// 옮겨 가는 동안 늘어난다. 누를 때는 placeIndicator(bar, 누른 버튼)(aria-selected도 옮겨 준다), 그릴 때마다(innerHTML로
// 다시 그린 뒤에도) placeIndicator(bar)를 부른다. bar.id로 옛 위치를 기억하므로 bar에는 바뀌지 않는 id가 있어야 한다.
// 처음 부를 때와 창 폭이 바뀌었을 때만 바로 놓는다(옆 글자가 길어져 막대 폭만 바뀐 것은 옮겨 가며 맞춘다).
const INDICATORS = new Map();
function placeIndicator(bar, picked) {
  if (!bar || !bar.id) return;
  if (picked) bar.querySelectorAll('[aria-selected]').forEach(b => b.setAttribute('aria-selected', String(b === picked)));
  const ind = bar.querySelector('.seg-indicator');
  const item = picked || bar.querySelector('[aria-selected="true"], [aria-pressed="true"]');
  if (!ind || !item) return;
  const b = bar.getBoundingClientRect(), r = item.getBoundingClientRect();
  if (!b.width) return;   // 숨어 있으면 다음에
  const L = r.left - b.left + bar.scrollLeft, R = L + r.width;
  const paint = () => {
    const now = document.getElementById(bar.id) || bar, el = now.querySelector('.seg-indicator'), st = INDICATORS.get(bar.id);
    if (!el || !st) return;
    el.style.left = st.l.value + 'px';
    el.style.width = Math.max(0, st.r.value - st.l.value) + 'px';
  };
  let st = INDICATORS.get(bar.id);
  if (!st || st.vw !== innerWidth) {   // 처음이거나 창 폭이 바뀌었으면 바로 놓는다
    st = { vw: innerWidth, l: createSpring(L, paint), r: createSpring(R, paint) };
    INDICATORS.set(bar.id, st); paint(); return;
  }
  const fast = { response: FEEL.frequent.response * 0.7, damping: FEEL.frequent.damping };
  const slow = { response: FEEL.frequent.response * 1.3, damping: Math.min(1, FEEL.frequent.damping + 0.12) };
  const right = L > st.l.target;
  st.l.to(L, right ? slow : fast);
  st.r.to(R, right ? fast : slow);
  paint();
}

// 버튼 → 패널: 누른 버튼 자리에서 부풀어 패널이 되고, 닫으면 그 자리로 줄어든 뒤 버튼으로 돌아온다(WWDC25).
// 패널이 떠 있으면(position fixed·absolute) 보이는 모양만, 제자리에 놓인 양식이면 높이도 함께 바뀐다.
// 쓰는 법: const m = createMorph(button, panel); button에서 m.open(), 패널 안 닫기 버튼과 Esc에서 m.close().
// 버튼과 패널은 hidden 속성으로 숨긴다(이 파일이 [hidden]{display:none!important}를 넣는다). 버튼에는 aria-controls=패널 id를 단다.
const MORPHS = [];
function createMorph(button, panel) {
  let geo = null, isOpen = false;
  const veil = document.createElement('div');
  veil.style.cssText = 'position:absolute;inset:0;border-radius:inherit;pointer-events:none;opacity:0;z-index:2';
  panel.appendChild(veil);
  if (getComputedStyle(panel).position === 'static') panel.style.position = 'relative';
  const clamp = v => Math.max(0, Math.min(1, v));
  const paint = p => {
    if (!geo) return;
    const q = clamp(p), k = 1 - q, { pr, br, float } = geo;
    if (float) {
      const rad = br.height / 2 + (geo.radius - br.height / 2) * q;
      panel.style.clipPath = q >= 1 ? '' : `inset(${(br.top - pr.top) * k}px ${(pr.right - br.right) * k}px ${(pr.bottom - br.bottom) * k}px ${(br.left - pr.left) * k}px round ${rad}px)`;
      panel.style.transformOrigin = `${br.left + br.width / 2 - pr.left}px ${br.top + br.height / 2 - pr.top}px`;
      panel.style.transform = p > 1 ? `scale(${1 + (p - 1) * 0.12})` : '';
    } else {
      const h = geo.startH + (geo.fullH - geo.startH) * p;
      panel.style.height = Math.max(0, h) + 'px';
      const shown = br.height + (Math.max(h, br.height) - br.height) * q;
      panel.style.clipPath = q >= 1 ? '' : `inset(0px 0px ${Math.max(0, h - shown)}px 0px round ${(br.height / 2) * k}px)`;
    }
    veil.style.opacity = String(clamp(1 - q / 0.45));   // 앞 절반: 버튼 색이 걷힌다
    for (const ch of panel.children) if (ch !== veil) ch.style.opacity = String(clamp((q - 0.4) / 0.45));   // 뒤 절반: 내용이 나타난다
  };
  const s = createSpring(0, paint);
  const reset = () => {
    panel.style.clipPath = ''; panel.style.transform = ''; veil.style.opacity = '0';
    for (const ch of panel.children) if (ch !== veil) ch.style.opacity = '';
  };
  let lastBr = null;   // 버튼이 보일 때 잰 자리. 닫히는 도중 다시 열면 버튼이 숨어 있으므로 이것을 쓴다
  const measure = () => {
    const pr = panel.getBoundingClientRect(), br = lastBr;
    const float = ['fixed', 'absolute'].includes(getComputedStyle(panel).position);
    geo = { pr, br, float, radius: parseFloat(getComputedStyle(panel).borderTopLeftRadius) || 28,
            startH: br.height, fullH: panel.scrollHeight };
  };
  const api = {
    get isOpen() { return isOpen; },
    open() {
      if (isOpen) return;
      isOpen = true;
      if (!button.hidden) { lastBr = button.getBoundingClientRect(); veil.style.background = getComputedStyle(button).backgroundColor; }
      button.hidden = true; panel.hidden = false; button.setAttribute('aria-expanded', 'true');
      // 제자리 양식은 여는 동안만 바깥을 자르고 다 열리면 되돌린다. 계속 자르면 안의 포커스 테두리가 가장자리에서 잘린다
      if (!['fixed', 'absolute'].includes(getComputedStyle(panel).position)) panel.style.overflow = 'hidden';
      measure(); paint(s.value);
      s.to(1, { ...FEEL.rare, onRest: () => { reset(); if (!geo.float) { panel.style.height = ''; panel.style.overflow = ''; } } });
      MORPHS.push(api);
    },
    close() {
      if (!isOpen) return;
      isOpen = false;
      measure(); paint(s.value);
      // 닫을 때는 튕기지 않는다. 버튼 크기에 거의 닿으면(1.5%) 바로 버튼으로 바꾼다(튕김 없는 스프링의 긴 꼬리)
      s.to(0, { response: FEEL.rare.response * 0.85, damping: 1, precision: 0.015,
        onRest: () => { reset(); panel.style.height = ''; panel.hidden = true; button.hidden = false; geo = null; } });
      button.setAttribute('aria-expanded', 'false');
      const i = MORPHS.indexOf(api); if (i >= 0) MORPHS.splice(i, 1);
    },
    toggle() { isOpen ? api.close() : api.open(); },
  };
  return api;
}
document.addEventListener('keydown', e => { if (e.key === 'Escape' && MORPHS.length) MORPHS[MORPHS.length - 1].close(); });

// 따라오는 단: 두 단 화면의 옆 단(col)이 스크롤을 따라온다. 화면보다 짧으면 위에 붙고,
// 길면 스크롤 방향을 따른다: 내려갈 땐 아래 끝이 보일 때까지 같이 내려가다 붙고, 올라갈 땐 위 끝이 보일 때까지 같이 올라가다 붙는다.
// 그래서 어느 부분도 계속 가려져 있지 않다. 좁은 화면(minWidth 미만)에서는 따라오지 않는다(한 단이라 다른 판을 가린다).
// col은 그리드·플렉스에서 옆 단 전체를 감싼 요소 하나여야 한다(섬마다 따로 붙이지 않는다).
function stickyColumn(col, { gap = 24, minWidth = 901 } = {}) {
  let lastY = scrollY, top = gap;
  const update = () => {
    if (innerWidth < minWidth) { col.style.position = ''; col.style.top = ''; return; }
    col.style.position = 'sticky'; col.style.alignSelf = 'start';
    const h = col.offsetHeight, vh = innerHeight;
    if (h + gap * 2 <= vh) top = gap;
    else top = Math.min(gap, Math.max(vh - h - gap, top - (scrollY - lastY)));
    lastY = scrollY;
    col.style.top = top + 'px';
  };
  addEventListener('scroll', update, { passive: true });
  addEventListener('resize', update);
  if (window.ResizeObserver) new ResizeObserver(update).observe(col);   // 양식을 펼치는 등 단 높이가 바뀔 때
  update();
}

// 높이가 바뀌어도 누른 버튼이 화면에서 움직이지 않게: change()로 탭·접기를 바꾼 뒤 그 버튼(get()이 찾음)이 밀린 만큼 되돌린다.
function keepInPlace(get, change) {
  const before = get() && get().getBoundingClientRect().top;
  change();
  const el = get();
  if (el == null || before == null) return;
  const d = el.getBoundingClientRect().top - before;
  if (Math.abs(d) > 0.5) scrollBy(0, d);
}

(() => { const st = document.createElement('style'); st.textContent = '[hidden]{display:none!important}'; document.head.appendChild(st); })();
