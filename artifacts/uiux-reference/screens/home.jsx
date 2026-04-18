// ============================================================
// HomeScreen — the "Studio" — main entry point
// Editorial workspace energy: greeting + composer + ticker +
// quick actions + at-a-glance dashboard.
// ============================================================

function HomeScreen({ setRoute }) {
  const [prompt, setPrompt] = React.useState('');
  const [niche, setNiche] = React.useState('tech');
  const currentNiche = NICHES.find(n => n.id === niche);

  const submit = () => {
    const q = prompt.trim() || 'Hook nào đang hiệu quả nhất trong ngách Công nghệ tuần này?';
    window.__gvQuery = q;
    window.__gvNiche = currentNiche.label;
    setRoute('answer');
  };

  return (
    <div style={{ background: 'var(--canvas)', minHeight: '100%' }}>
      {/* Ticker — moving headlines */}
      <Ticker />

      <div style={{ maxWidth: 1320, margin: '0 auto', padding: '36px 28px 80px' }}>

        {/* App-style greeting */}
        <section className="fade-up" style={{ marginBottom: 28 }}>
          <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16, marginBottom: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span className="chip chip-lime"><span className="live-dot" style={{ background: 'var(--ink)' }}></span>LIVE · CẬP NHẬT 2 PHÚT TRƯỚC</span>
              <span className="chip mono" style={{ fontSize: 11 }}>THỨ BẢY · 18.04</span>
            </div>
            <NichePicker niche={niche} setNiche={setNiche} />
          </div>
          <div style={{ maxWidth: 880 }}>
            <h1 className="tight" style={{
              fontSize: 'clamp(36px, 4.6vw, 60px)',
              lineHeight: 1.02, margin: 0, color: 'var(--ink)',
              letterSpacing: '-0.04em', fontWeight: 600,
            }}>
              Chào An. Hôm nay <span style={{
                background: 'var(--accent)', color: 'white',
                padding: '0 10px', borderRadius: 10, display: 'inline-block', transform: 'rotate(-1deg)',
              }}>ngách Tech</span> có <span style={{ color: 'rgb(0, 159, 250)' }}>3 hook</span> mới đang nổ.
            </h1>
          </div>
        </section>

        {/* Composer — bigger, more deliberate */}
        <section className="fade-up" style={{ marginBottom: 28, animationDelay: '60ms' }}>
          <Composer prompt={prompt} setPrompt={setPrompt} niche={currentNiche} onSubmit={submit} />
        </section>

        {/* Suggested prompts — magazine style */}
        <section className="fade-up" style={{ marginBottom: 56, animationDelay: '120ms' }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {SUGGESTED_PROMPTS.map(p => (
              <button key={p} className="chip" onClick={() => setPrompt(p)} style={{ cursor: 'pointer' }}>
                <Icon name="sparkle" size={11} style={{ color: 'var(--accent)' }} />
                {p}
              </button>
            ))}
          </div>
        </section>

        <hr className="rule" style={{ marginBottom: 36 }} />

        {/* Morning ritual — 3 scripts ready today */}
        <section className="fade-up" style={{ marginBottom: 48, animationDelay: '140ms' }}>
          <SectionHeader kicker="SÁNG NAY · 06:00" title="3 kịch bản sẵn sàng cho bạn" caption="Tổng hợp từ pattern thắng trong ngách của bạn qua đêm qua." />
          <MorningRitual setRoute={setRoute} />
        </section>

        <hr className="rule" style={{ marginBottom: 36 }} />

        {/* Two-column: Quick actions + Pulse */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 2fr) minmax(0, 1fr)',
          gap: 36, marginBottom: 56,
        }} className="home-grid">
          <div>
            <SectionHeader kicker="THAO TÁC" title="Bắt đầu nhanh" caption="6 cửa vào — chọn cửa hợp với ý tưởng của bạn." />
            <QuickActions setRoute={setRoute} />
          </div>
          <div>
            <SectionHeader kicker="NHỊP TUẦN" title="Pulse" caption="Tín hiệu sống trong ngách của bạn." />
            <PulseCard />
          </div>
        </div>

        {/* Hooks of the week */}
        <section style={{ marginBottom: 48 }}>
          <SectionHeader kicker="BẢNG XẾP HẠNG" title="Hook đang chạy" caption="Top 6 mẫu hook 3 giây với tăng trưởng nhanh nhất tuần qua." />
          <HooksTable />
        </section>

        {/* Editor's pick — breakout videos */}
        <section style={{ marginBottom: 24 }}>
          <SectionHeader kicker="BIÊN TẬP CHỌN" title="3 video đột phá" caption="View vượt 10× so với trung bình kênh trong 48 giờ qua." action={<button className="btn btn-ghost" onClick={() => setRoute('trends')}><span>Xem tất cả</span><Icon name="arrow-right" size={12} /></button>} />
          <BreakoutGrid setRoute={setRoute} />
        </section>
      </div>

      <style>{`
        @media (max-width: 900px) {
          .home-grid { grid-template-columns: 1fr !important; }
          .quick-grid { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </div>
  );
}

// ----- Ticker -----
function Ticker() {
  const items = [
    { tag: 'BREAKOUT', text: '@aifreelance — "5 app AI mà chưa ai nói" · 234K view trong 18h' },
    { tag: 'HOOK MỚI', text: '"Khi bạn ___" tăng 248% sử dụng tuần này' },
    { tag: 'CẢNH BÁO', text: 'Format unboxing dài >60s đang giảm 18% reach trong Tech' },
    { tag: 'KOL NỔI', text: '@minhtuan.dev tăng 34% follower trong 7 ngày' },
    { tag: 'ÂM THANH', text: 'Sound "Lo-fi typewriter" đang được gắn vào 1.2K video Edu' },
  ];
  const doubled = [...items, ...items];
  return (
    <div style={{
      borderBottom: '1px solid var(--rule)',
      background: 'var(--ink)', color: 'var(--canvas)',
      overflow: 'hidden', whiteSpace: 'nowrap',
      padding: '8px 0',
    }}>
      <div className="marquee-track">
        {doubled.map((it, i) => (
          <span key={i} className="mono" style={{ fontSize: 11, display: 'inline-flex', alignItems: 'center', gap: 10 }}>
            <span style={{ color: 'var(--accent)', fontWeight: 600 }}>{it.tag}</span>
            <span style={{ opacity: 0.85 }}>{it.text}</span>
            <span style={{ opacity: 0.4 }}>·</span>
          </span>
        ))}
      </div>
    </div>
  );
}

// ----- Section header (editorial) -----
function SectionHeader({ kicker, title, caption, action }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between',
      gap: 16, marginBottom: 16,
    }}>
      <div>
        <div className="mono uc" style={{ fontSize: 10, color: 'var(--accent-deep)', marginBottom: 6, fontWeight: 600 }}>● {kicker}</div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
          <h2 className="tight" style={{ margin: 0, fontSize: 28, lineHeight: 1, color: 'var(--ink)', fontWeight: 600, letterSpacing: '-0.03em' }}>{title}</h2>
          {caption && <div style={{ fontSize: 13, color: 'var(--ink-3)' }}>{caption}</div>}
        </div>
      </div>
      {action}
    </div>
  );
}

// ----- Niche picker pill -----
function NichePicker({ niche, setNiche }) {
  const [open, setOpen] = React.useState(false);
  const current = NICHES.find(n => n.id === niche);
  return (
    <div style={{ position: 'relative' }}>
      <button onClick={() => setOpen(o => !o)} style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '10px 16px',
        border: '1px solid var(--ink)', borderRadius: 999,
        background: 'var(--paper)', fontSize: 13, fontWeight: 500,
      }}>
        <span className="mono uc" style={{ fontSize: 9, color: 'var(--ink-4)' }}>NGÁCH</span>
        <span>{current?.label}</span>
        <span style={{ color: 'var(--accent-deep)', fontSize: 12 }}>↓ {current?.hot} hot</span>
      </button>
      {open && (
        <>
          <div onClick={() => setOpen(false)} style={{ position: 'fixed', inset: 0, zIndex: 20 }} />
          <div style={{
            position: 'absolute', top: 'calc(100% + 6px)', right: 0, zIndex: 21,
            background: 'var(--paper)', border: '1px solid var(--ink)', borderRadius: 8,
            padding: 6, minWidth: 240, boxShadow: '0 12px 32px -12px rgba(0,0,0,0.2)',
          }}>
            {NICHES.map(n => (
              <button key={n.id} onClick={() => { setNiche(n.id); setOpen(false); }} style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                width: '100%', padding: '8px 10px', borderRadius: 6,
                fontSize: 13,
                background: n.id === niche ? 'var(--canvas-2)' : 'transparent',
                color: 'var(--ink)',
                textAlign: 'left',
              }}
                onMouseEnter={e => { if (n.id !== niche) e.currentTarget.style.background = 'var(--canvas-2)'; }}
                onMouseLeave={e => { if (n.id !== niche) e.currentTarget.style.background = 'transparent'; }}
              >
                <span>{n.label}</span>
                <span className="mono" style={{ fontSize: 10, color: 'var(--ink-4)' }}>{n.count}</span>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ----- Composer -----
function Composer({ prompt, setPrompt, niche, onSubmit }) {
  return (
    <div style={{
      background: 'var(--paper)',
      border: '2px solid var(--ink)',
      borderRadius: 20,
      padding: 4,
      boxShadow: '6px 6px 0 var(--ink)',
    }}>
      <div style={{ padding: '18px 22px 8px' }}>
        <textarea
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); onSubmit && onSubmit(); } }}
          placeholder={`Hỏi về hook, trend, hay kênh ${niche.label}…`}
          rows={3}
          style={{
            width: '100%', border: 0, outline: 0, resize: 'none',
            background: 'transparent', fontFamily: 'var(--sans)',
            fontSize: 17, lineHeight: 1.5, color: 'var(--ink)',
          }}
        />
      </div>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '10px 14px',
        borderTop: '1px solid var(--rule)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <button className="chip" title="Đính kèm link / file"><Icon name="paperclip" size={12} /></button>
          <button className="chip"><Icon name="film" size={12} /> Dán link video</button>
          <button className="chip hide-mobile"><Icon name="eye" size={12} /> Dán @handle</button>
          <span className="chip" style={{ color: 'var(--ink-4)' }}>
            <span className="mono">{niche.count.toLocaleString()}+ video</span>
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button className="chip hide-mobile"><Icon name="mic" size={12} /></button>
          <button className="btn btn-accent" onClick={onSubmit} style={{
            opacity: 1, cursor: 'pointer',
          }}>
            <span>Gửi</span>
            <Icon name="arrow-up" size={12} />
          </button>
        </div>
      </div>
    </div>
  );
}

// ----- Quick actions grid (more editorial) -----
function QuickActions({ setRoute }) {
  const map = { video: 'video', channel: 'channel', trends: 'trends', script: 'script', kol: 'kol', consult: 'home' };
  return (
    <div className="quick-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 1, background: 'var(--rule)', border: '1px solid var(--rule)', borderRadius: 8, overflow: 'hidden' }}>
      {QUICK_ACTIONS.map((a, i) => (
        <button key={a.id} onClick={() => setRoute(map[a.id])} style={{
          padding: '22px 20px',
          background: 'var(--paper)',
          textAlign: 'left',
          display: 'flex', flexDirection: 'column', gap: 10,
          minHeight: 150,
          transition: 'background 0.15s ease',
        }}
          onMouseEnter={e => e.currentTarget.style.background = 'var(--canvas-2)'}
          onMouseLeave={e => e.currentTarget.style.background = 'var(--paper)'}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
            <div style={{
              width: 32, height: 32, borderRadius: 6,
              border: '1px solid var(--rule)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: 'var(--ink-2)', background: 'var(--canvas)',
            }}>
              <Icon name={a.icon} size={15} />
            </div>
            <span className="mono uc" style={{ fontSize: 9, color: 'var(--ink-4)' }}>0{i+1}</span>
          </div>
          <div>
            <div className="tight" style={{ fontSize: 18, lineHeight: 1.1, color: 'var(--ink)', fontWeight: 600, letterSpacing: '-0.02em' }}>{a.title}</div>
            <div style={{ fontSize: 12, color: 'var(--ink-3)', marginTop: 4 }}>{a.desc}</div>
          </div>
        </button>
      ))}
    </div>
  );
}

// ----- Pulse card (mini dashboard) -----
function PulseCard() {
  return (
    <div className="card" style={{ padding: 22, display: 'flex', flexDirection: 'column', gap: 18 }}>
      <div>
        <div className="mono uc" style={{ fontSize: 9, color: 'var(--ink-4)', marginBottom: 6 }}>NHỊP NGÁCH TECH · 7 NGÀY</div>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 10, flexWrap: 'wrap' }}>
          <div className="bignum">42.8M</div>
          <div style={{ paddingBottom: 8, color: 'var(--pos-deep)', fontSize: 13, fontWeight: 600, whiteSpace: 'nowrap' }}>
            ▲ 18.4%
          </div>
        </div>
        <div style={{ fontSize: 12, color: 'var(--ink-3)', marginTop: 4 }}>Tổng view trên 661 video theo dõi</div>
      </div>

      <Sparkline />

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, paddingTop: 14, borderTop: '1px solid var(--rule)' }}>
        <Stat label="VIDEO MỚI" value="248" delta="+12%" />
        <Stat label="CREATOR" value="89" delta="+3" />
        <Stat label="VIRAL" value="14" delta="+6" hot />
        <Stat label="HOOK MỚI" value="3" delta="đột phá" hot />
      </div>
    </div>
  );
}

function Stat({ label, value, delta, hot }) {
  const isNeg = typeof delta === 'string' && delta.trim().startsWith('-');
  const trendColor = isNeg ? 'var(--neg-deep)' : 'var(--pos-deep)';
  return (
    <div>
      <div className="mono uc" style={{ fontSize: 9, color: 'var(--ink-4)', fontWeight: 600 }}>{label}</div>
      <div className="tight" style={{ fontSize: 26, lineHeight: 1.1, marginTop: 2, fontWeight: 600, letterSpacing: '-0.03em' }}>{value}</div>
      <div className="mono" style={{ fontSize: 10, color: hot ? trendColor : 'var(--ink-3)', marginTop: 2, fontWeight: hot ? 700 : 400 }}>{delta}</div>
    </div>
  );
}

function Sparkline({ data = [22, 28, 24, 30, 36, 32, 48, 42, 50, 58, 54, 68, 72] }) {
  const w = 280, h = 60;
  const max = Math.max(...data);
  const step = w / (data.length - 1);
  const pts = data.map((v, i) => `${i * step},${h - (v / max) * h}`).join(' ');
  const area = `M0,${h} L${pts.split(' ').join(' L')} L${w},${h} Z`;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="spark" style={{ width: '100%', height: 60 }}>
      <path d={area} fill="var(--pos-soft)" />
      <polyline points={pts} fill="none" stroke="var(--pos)" strokeWidth="1.5" />
      {data.map((v, i) => i === data.length - 1 && (
        <circle key={i} cx={i * step} cy={h - (v / max) * h} r="3" fill="var(--pos)" />
      ))}
    </svg>
  );
}

// ----- Hooks Table -----
function HooksTable() {
  return (
    <div className="card" style={{ overflow: 'hidden' }}>
      <div style={{
        display: 'grid', gridTemplateColumns: '60px minmax(180px, 2fr) 100px 90px 100px minmax(180px, 2fr)',
        padding: '10px 18px',
        borderBottom: '1px solid var(--rule)', background: 'var(--canvas-2)',
      }}>
        {['#', 'MẪU HOOK', 'TĂNG', 'LƯỢT DÙNG', 'VIEW TB', 'VÍ DỤ'].map(h => (
          <div key={h} className="mono uc" style={{ fontSize: 9.5, color: 'var(--ink-4)', fontWeight: 600 }}>{h}</div>
        ))}
      </div>
      {HOOKS.map((h, i) => (
        <div key={h.pattern} className="hook-row" style={{
          display: 'grid', gridTemplateColumns: '60px minmax(180px, 2fr) 100px 90px 100px minmax(180px, 2fr)',
          padding: '14px 18px',
          borderBottom: i === HOOKS.length - 1 ? 0 : '1px solid var(--rule)',
          alignItems: 'center', cursor: 'pointer',
          transition: 'background 0.15s ease',
        }}
          onMouseEnter={e => e.currentTarget.style.background = 'var(--canvas-2)'}
          onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
        >
          <div className="mono" style={{ fontSize: 11, color: 'var(--ink-4)' }}>0{i+1}</div>
          <div className="tight" style={{ fontSize: 17, color: 'var(--ink)', fontWeight: 600, letterSpacing: '-0.02em' }}>"{h.pattern}"</div>
          <div className="mono" style={{ fontSize: 13, color: 'var(--pos-deep)', fontWeight: 700 }}>{h.delta}</div>
          <div className="mono" style={{ fontSize: 12, color: 'var(--ink-2)' }}>{h.uses.toLocaleString()}</div>
          <div className="mono" style={{ fontSize: 12, color: 'var(--ink-2)' }}>{h.avg}</div>
          <div style={{ fontSize: 12, color: 'var(--ink-3)' }}>"{h.sample}"</div>
        </div>
      ))}
    </div>
  );
}

// ----- Breakout grid (3 large feature tiles) -----
function BreakoutGrid({ setRoute }) {
  const breakouts = VIDEOS.filter(v => v.breakout || v.viral).slice(0, 3);
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 18 }}>
      {breakouts.map((v, i) => (
        <button key={v.id} onClick={() => setRoute('video')} className="tile" style={{
          textAlign: 'left', display: 'flex', flexDirection: 'column', gap: 12,
        }}>
          <div style={{
            aspectRatio: '4/5', borderRadius: 10, overflow: 'hidden',
            background: v.bg, position: 'relative',
            border: '1px solid var(--rule)',
          }}>
            {/* mock video tile content */}
            <div style={{ position: 'absolute', inset: 0, padding: 14, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', color: 'white' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{
                  background: 'var(--accent)', padding: '3px 8px', borderRadius: 4,
                  fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em',
                }}>BREAKOUT</span>
                <span className="mono" style={{ fontSize: 11 }}>{v.dur}</span>
              </div>
              <div className="tight" style={{ fontSize: 22, lineHeight: 1.1, textShadow: '0 2px 12px rgba(0,0,0,0.5)', fontWeight: 600, letterSpacing: '-0.02em' }}>
                "{v.title}"
              </div>
            </div>
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
              <span className="mono" style={{ fontSize: 11, color: 'var(--ink-3)', fontWeight: 600 }}>{v.creator}</span>
              <span className="mono" style={{ fontSize: 11, color: 'var(--accent-deep)', fontWeight: 700 }}>↑ {v.views}</span>
            </div>
            <div style={{ fontSize: 12, color: 'var(--ink-3)' }}>
              Hook · <span style={{ color: 'var(--ink-2)', fontWeight: 600 }}>"{v.hook}"</span>
            </div>
          </div>
        </button>
      ))}
    </div>
  );
}

window.HomeScreen = HomeScreen;

// ----- Morning ritual — 3 scripts ready -----
function MorningRitual({ setRoute }) {
  const scripts = [
    { badge: 'HOOK #1', title: 'Mình vừa test iPad Pro M4 và thật sự…', est: '~62K · 72% ret', why: 'Dựa trên 3 video thắng đêm qua trong ngách Tech', shots: 6, len: '32s' },
    { badge: 'HOOK #2', title: 'Không ai nói với bạn là Cursor có chế độ này', est: '~41K · 68% ret', why: '@huy.codes vừa đạt 156K với pattern tương tự', shots: 5, len: '28s' },
    { badge: 'HOOK #3', title: 'Lướt thấy AI này mà không thể tin là free', est: '~34K · 61% ret', why: 'Đang trend · 182% growth 3 ngày qua', shots: 5, len: '22s' },
  ];
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }} className="morning-grid">
      {scripts.map((s, i) => (
        <button key={i} onClick={() => setRoute('script')} style={{
          textAlign: 'left', cursor: 'pointer',
          background: i === 0 ? 'var(--ink)' : 'var(--paper)',
          color: i === 0 ? 'var(--canvas)' : 'var(--ink)',
          border: '1px solid var(--ink)',
          padding: '18px 18px 16px', display: 'flex', flexDirection: 'column', gap: 10,
          minHeight: 180, transition: 'transform 0.15s, box-shadow 0.15s',
        }}
        onMouseEnter={e => { e.currentTarget.style.transform = 'translate(-2px, -2px)'; e.currentTarget.style.boxShadow = (i === 0 ? '4px 4px 0 var(--accent)' : '4px 4px 0 var(--ink)'); }}
        onMouseLeave={e => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.boxShadow = 'none'; }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span className="mono" style={{
              background: i === 0 ? 'var(--accent)' : 'var(--accent-soft)',
              color: i === 0 ? 'white' : 'var(--accent-deep)',
              padding: '3px 8px', borderRadius: 3, fontSize: 10, fontWeight: 600, letterSpacing: '0.08em',
            }}>{s.badge}</span>
            <span className="mono" style={{ fontSize: 10, opacity: 0.6 }}>{s.shots} shot · {s.len}</span>
          </div>
          <div style={{ fontFamily: 'var(--serif)', fontSize: 20, lineHeight: 1.2, fontWeight: 500, letterSpacing: '-0.01em', textWrap: 'pretty', flex: 1 }}>
            "{s.title}"
          </div>
          <div style={{ fontSize: 12, opacity: 0.7, lineHeight: 1.5 }}>{s.why}</div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid ' + (i === 0 ? 'rgba(255,255,255,0.15)' : 'var(--rule)'), paddingTop: 10, marginTop: 4 }}>
            <span className="mono" style={{ fontSize: 11, color: i === 0 ? 'rgb(0, 159, 250)' : 'rgb(0, 159, 250)' }}>▲ {s.est}</span>
            <span style={{ fontSize: 11, fontWeight: 500 }} className="mono">Mở kịch bản →</span>
          </div>
        </button>
      ))}
      <style>{`
        @media (max-width: 940px) { .morning-grid { grid-template-columns: 1fr !important; } }
      `}</style>
    </div>
  );
}
