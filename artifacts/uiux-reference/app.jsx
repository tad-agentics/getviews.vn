// ============================================================
// App root + Tweaks
// ============================================================

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "theme": "light",
  "density": "comfortable",
  "accent": "tiktok",
  "showTicker": true,
  "serifDisplay": "Space Grotesk",
  "sansUI": "Space Grotesk",
  "startScreen": "home"
}/*EDITMODE-END*/;

const ACCENTS = {
  tiktok: { v: '#FE2C55', d: '#D11840', s: '#FFE8ED', v2: '#25F4EE', d2: '#06B6B0', s2: '#D8FBFA' },
  pink:   { v: '#EC4899', d: '#BE1F6D', s: '#FCE7F3', v2: '#A855F7', d2: '#7E22CE', s2: '#F3E8FF' },
  blue:   { v: '#3B82F6', d: '#1D4ED8', s: '#DBEAFE', v2: '#06B6D4', d2: '#0E7490', s2: '#CFFAFE' },
  coral:  { v: 'oklch(0.68 0.22 25)',  d: 'oklch(0.5 0.22 25)',  s: 'oklch(0.94 0.04 25)', v2: '#25F4EE', d2: '#06B6B0', s2: '#D8FBFA' },
  ink:    { v: '#2A2A33',              d: '#0A0D12',             s: '#E5E7EB',             v2: '#3B82F6', d2: '#1D4ED8', s2: '#DBEAFE' },
  green:  { v: '#10B981',              d: '#047857',             s: '#D1FAE5',             v2: '#8B5CF6', d2: '#6D28D9', s2: '#EDE9FE' },
};

function App() {
  const [tweaks, setTweaks] = React.useState(TWEAK_DEFAULTS);
  const [route, setRouteRaw] = React.useState(() => {
    return localStorage.getItem('gv-route') || tweaks.startScreen || 'home';
  });
  const [tweakOpen, setTweakOpen] = React.useState(false);

  const setRoute = (r) => {
    // MVP: Creator only. The legacy 'seller' route is folded back to home.
    if (r === 'seller') r = 'home';
    setRouteRaw(r);
    localStorage.setItem('gv-route', r);
    window.scrollTo(0, 0);
  };

  // One-time cleanup: if a returning user has 'seller' persisted, reset to home.
  React.useEffect(() => {
    if (route === 'seller') setRoute('home');
    // Clear legacy role key so a fresh install is truly creator-only.
    localStorage.removeItem('gv-role');
  }, []); // eslint-disable-line

  // Apply tweaks to root
  React.useEffect(() => {
    document.documentElement.setAttribute('data-theme', tweaks.theme);
    document.documentElement.setAttribute('data-density', tweaks.density);
    const a = ACCENTS[tweaks.accent] || ACCENTS.tiktok;
    document.documentElement.style.setProperty('--accent', a.v);
    document.documentElement.style.setProperty('--accent-deep', a.d);
    document.documentElement.style.setProperty('--accent-soft', a.s);
    document.documentElement.style.setProperty('--accent-2', a.v2);
    document.documentElement.style.setProperty('--accent-2-deep', a.d2);
    document.documentElement.style.setProperty('--accent-2-soft', a.s2);
    document.documentElement.style.setProperty('--serif', `'${tweaks.serifDisplay}', Georgia, serif`);
    document.documentElement.style.setProperty('--sans', `'${tweaks.sansUI}', -apple-system, sans-serif`);
  }, [tweaks]);

  // Tweaks bridge
  React.useEffect(() => {
    function onMsg(e) {
      if (e.data?.type === '__activate_edit_mode') setTweakOpen(true);
      if (e.data?.type === '__deactivate_edit_mode') setTweakOpen(false);
    }
    window.addEventListener('message', onMsg);
    window.parent.postMessage({ type: '__edit_mode_available' }, '*');
    return () => window.removeEventListener('message', onMsg);
  }, []);

  const update = (patch) => {
    const next = { ...tweaks, ...patch };
    setTweaks(next);
    window.parent.postMessage({ type: '__edit_mode_set_keys', edits: patch }, '*');
  };

  // Onboarding is full-bleed
  if (route === 'onboarding') {
    return <OnboardingScreen setRoute={setRoute} />;
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }} data-role="creator" data-screen-label={
      route === 'home' ? '01 Studio (Creator Home)' :
      route === 'trends' ? '02 Xu Hướng' :
      route === 'video' ? '03 Phân Tích Video' :
      route === 'channel' ? '04 Phân Tích Kênh' :
      route === 'kol' ? '05 KOL Inspiration' :
      route === 'script' ? '06 Kịch Bản' :
      route === 'settings' ? '07 Cài Đặt' :
      route === 'answer' ? '08 Nghiên Cứu (Answer)' :
      'Studio'
    }>
      <Sidebar route={route} setRoute={setRoute} />
      <main style={{ flex: 1, minWidth: 0 }}>
        <TopBar route={route} setRoute={setRoute} />
        {route === 'home'     && <HomeScreen     setRoute={setRoute} />}
        {route === 'trends'   && <TrendsScreen   setRoute={setRoute} />}
        {route === 'video'    && <VideoScreen    setRoute={setRoute} />}
        {route === 'channel'  && <ChannelScreen  setRoute={setRoute} />}
        {route === 'channels' && <ChannelScreen  setRoute={setRoute} />}
        {route === 'kol'      && <KolScreen      setRoute={setRoute} />}
        {route === 'script'   && <ScriptScreen   setRoute={setRoute} />}
        {route === 'settings' && <SettingsScreen />}
        {route === 'answer'   && <AnswerScreen   setRoute={setRoute} />}
      </main>

      {/* Mini quick-jump (always visible bottom right when no tweaks) */}
      {!tweakOpen && <QuickJump route={route} setRoute={setRoute} />}
      {tweakOpen && <TweakPanel tweaks={tweaks} update={update} onClose={() => setTweakOpen(false)} setRoute={setRoute} />}
    </div>
  );
}

function QuickJump({ route, setRoute }) {
  const items = [
    { id: 'home', label: 'Studio', i: 'chat' },
    { id: 'answer', label: 'Nghiên cứu', i: 'sparkle' },
    { id: 'trends', label: 'Trends', i: 'trend' },
    { id: 'kol', label: 'KOL', i: 'users' },
    { id: 'script', label: 'Script', i: 'script' },
    { id: 'onboarding', label: 'Onboard', i: 'sparkle' },
  ];
  return (
    <div style={{
      position: 'fixed', bottom: 16, left: '50%', transform: 'translateX(-50%)',
      background: 'var(--ink)', color: 'var(--canvas)', borderRadius: 999,
      padding: 4, display: 'flex', gap: 2, zIndex: 50,
      boxShadow: '0 12px 40px -10px rgba(0,0,0,0.4)',
    }}>
      {items.map(it => (
        <button key={it.id} onClick={() => setRoute(it.id)} style={{
          padding: '7px 14px', borderRadius: 999,
          background: route === it.id ? 'var(--accent)' : 'transparent',
          color: route === it.id ? 'white' : 'var(--canvas)',
          fontSize: 11, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 5,
        }}>
          <Icon name={it.i} size={11} />{it.label}
        </button>
      ))}
    </div>
  );
}

function TweakPanel({ tweaks, update, onClose, setRoute }) {
  return (
    <div className="tweaks-panel">
      <div style={{ padding: '12px 14px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'var(--ink)', color: 'var(--canvas)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Icon name="settings" size={13} />
          <span className="mono uc" style={{ fontSize: 10 }}>TWEAKS</span>
        </div>
        <button onClick={onClose} style={{ color: 'var(--canvas)' }}><Icon name="x" size={14} /></button>
      </div>
      <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 18, maxHeight: '70vh', overflowY: 'auto' }}>
        <TweakRow label="Chế độ">
          <Seg value={tweaks.theme} onChange={v => update({ theme: v })} options={[['light', 'Sáng'], ['dark', 'Tối']]} />
        </TweakRow>
        <TweakRow label="Mật độ">
          <Seg value={tweaks.density} onChange={v => update({ density: v })} options={[['comfortable', 'Thoáng'], ['compact', 'Đặc']]} />
        </TweakRow>
        <TweakRow label="Màu nhấn">
          <div style={{ display: 'flex', gap: 6 }}>
            {Object.keys(ACCENTS).map(k => (
              <button key={k} onClick={() => update({ accent: k })} style={{
                width: 24, height: 24, borderRadius: '50%',
                background: ACCENTS[k].v,
                border: tweaks.accent === k ? '2px solid var(--ink)' : '2px solid transparent',
                outline: tweaks.accent === k ? '1px solid var(--canvas)' : 'none',
                outlineOffset: -3,
              }} title={k} />
            ))}
          </div>
        </TweakRow>
        <TweakRow label="Font display">
          <select value={tweaks.serifDisplay} onChange={e => update({ serifDisplay: e.target.value })} style={selectStyle}>
            <option>Space Grotesk</option>
            <option>Instrument Serif</option>
            <option>Fraunces</option>
            <option>Manrope</option>
            <option>Inter</option>
          </select>
        </TweakRow>
        <TweakRow label="Font UI">
          <select value={tweaks.sansUI} onChange={e => update({ sansUI: e.target.value })} style={selectStyle}>
            <option>Space Grotesk</option>
            <option>Geist</option>
            <option>Inter</option>
            <option>IBM Plex Sans</option>
            <option>Manrope</option>
          </select>
        </TweakRow>
        <TweakRow label="Ticker tin nóng">
          <Seg value={tweaks.showTicker ? 'on' : 'off'} onChange={v => update({ showTicker: v === 'on' })} options={[['on', 'Bật'], ['off', 'Tắt']]} />
        </TweakRow>

        <hr className="rule" />
        <div className="mono uc" style={{ fontSize: 9, color: 'var(--ink-4)' }}>NHẢY TỚI MÀN HÌNH</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
          {[
            ['home', 'Studio'], ['trends', 'Xu Hướng'],
            ['video', 'Video'], ['channel', 'Kênh'],
            ['kol', 'KOL'], ['script', 'Kịch Bản'],
            ['onboarding', 'Onboarding'], ['settings', 'Cài Đặt'],
          ].map(([id, label]) => (
            <button key={id} onClick={() => setRoute(id)} style={{
              padding: '6px 8px', border: '1px solid var(--rule)',
              borderRadius: 4, fontSize: 11, textAlign: 'left',
              background: 'var(--canvas-2)',
            }}>{label}</button>
          ))}
        </div>
      </div>
    </div>
  );
}

const selectStyle = {
  width: '100%', padding: '6px 8px',
  border: '1px solid var(--rule)', borderRadius: 4,
  fontSize: 12, background: 'var(--canvas)', color: 'var(--ink)',
};

function TweakRow({ label, children }) {
  return (
    <div>
      <div style={{ fontSize: 11, color: 'var(--ink-3)', marginBottom: 6, fontWeight: 500 }}>{label}</div>
      {children}
    </div>
  );
}

function Seg({ value, onChange, options }) {
  return (
    <div style={{ display: 'flex', border: '1px solid var(--rule)', borderRadius: 4, overflow: 'hidden', background: 'var(--canvas-2)' }}>
      {options.map(([v, l]) => (
        <button key={v} onClick={() => onChange(v)} style={{
          flex: 1, padding: '6px 8px',
          background: value === v ? 'var(--ink)' : 'transparent',
          color: value === v ? 'var(--canvas)' : 'var(--ink-2)',
          fontSize: 11, fontWeight: 500,
        }}>{l}</button>
      ))}
    </div>
  );
}

window.App = App;

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
