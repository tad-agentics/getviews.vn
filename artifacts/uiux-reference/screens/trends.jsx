// ============================================================
// Trends Screen — Xu Hướng / Discovery
// Editorial 'newsroom' grid with sidebar of curated picks
// ============================================================

function TrendsScreen({ setRoute }) {
  const [view, setView] = React.useState('grid');
  const [filter, setFilter] = React.useState('all');
  const [sort, setSort] = React.useState('newest');

  return (
    <div style={{ background: 'var(--canvas)', minHeight: '100%' }}>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(0, 1fr) 320px',
        gap: 0,
      }} className="trends-layout">
        {/* Main */}
        <div style={{ padding: '24px 28px 60px', borderRight: '1px solid var(--rule)' }}>
          {/* Hero card — week summary */}
          <div style={{
            background: 'var(--ink)', color: 'var(--canvas)',
            borderRadius: 12, padding: '28px 32px',
            display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 32,
            marginBottom: 28,
          }} className="trends-hero">
            <div>
              <div className="mono uc" style={{ fontSize: 9, color: 'var(--ink-4)', marginBottom: 8 }}>TUẦN 16 · 12—18 THÁNG 4</div>
              <div className="tight" style={{ fontSize: 36, lineHeight: 1, marginBottom: 6 }}>
                661 video <span style={{ color: 'var(--accent)' }}>được giải mã</span>
              </div>
              <div style={{ fontSize: 12, color: 'var(--ink-4)', maxWidth: 320 }}>
                Cập nhật mỗi 15 phút từ 89 creator hàng đầu trong ngách Tech.
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, alignContent: 'center' }}>
              <HeroStat label="VIEW TỔNG" value="42.8M" delta="+18%" />
              <HeroStat label="TĂNG TUẦN TRƯỚC" value="+18%" delta="3 tuần liên tiếp" />
              <HeroStat label="ĐỘT PHÁ" value="14" delta="↑ 6 vs tuần trước" />
              <HeroStat label="HOOK MỚI" value="3" delta="chưa xuất hiện" />
            </div>
            <div>
              <div className="mono uc" style={{ fontSize: 9, color: 'var(--ink-4)', marginBottom: 8 }}>TÓM TẮT BIÊN TẬP</div>
              <div className="tight" style={{ fontSize: 16, lineHeight: 1.4, color: 'var(--canvas)' }}>
                Format <em>"5 thứ chưa ai nói"</em> đang thay thế listicle dài. Video AI tools dẫn đầu reach. Unboxing &gt;60s đang tụt 18%.
              </div>
            </div>
          </div>

          {/* Toolbar */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            marginBottom: 20, gap: 16, flexWrap: 'wrap',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <h2 className="tight" style={{ margin: 0, fontSize: 26 }}>Khám phá <span className="mono" style={{ fontSize: 13, color: 'var(--ink-4)' }}>661</span></h2>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <SearchInput placeholder="Tìm video, hook, creator…" />
              <Pill>Niche ▾</Pill>
              <Pill>Mới nhất ▾</Pill>
              <Pill>Loại ▾</Pill>
              <Pill active>100K+</Pill>
              <Pill>500K+</Pill>
              <Pill>1M+</Pill>
              <div style={{ display: 'flex', border: '1px solid var(--rule)', borderRadius: 999, padding: 2, background: 'var(--paper)' }}>
                {['grid', 'list'].map(v => (
                  <button key={v} onClick={() => setView(v)} style={{
                    width: 28, height: 24, borderRadius: 999,
                    background: view === v ? 'var(--ink)' : 'transparent',
                    color: view === v ? 'var(--canvas)' : 'var(--ink-3)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                    <Icon name={v} size={12} />
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Grid */}
          {view === 'grid' ? <VideoGrid setRoute={setRoute} /> : <VideoList setRoute={setRoute} />}
        </div>

        {/* Right rail */}
        <aside style={{ padding: '24px 22px', display: 'flex', flexDirection: 'column', gap: 24 }} className="trends-rail">
          <RailSection
            kicker="VIDEO NÊN XEM"
            title="Hôm nay"
            items={[
              { tag: 'Breakout tuần này', body: '@aifreelance — "5 app AI mà chưa ai nói" · 234K view trong 18h', accent: true },
              { tag: 'Đang viral', body: '@phuongmy — "Đây là cái thế giới…" · 175K view, lan ra Threads' },
              { tag: 'Đáng học', body: '@sammie.tech — cấu trúc 3-act mới với hook 1.8s' },
            ]}
          />
          <RailSection
            kicker="ÂM THANH ĐANG LÊN"
            title="Sounds"
            items={[
              { tag: 'Lo-fi typewriter', body: '+812% gắn vào video Edu trong 7 ngày' },
              { tag: 'Original — @aifreelance', body: 'Voice-over "Mà chưa ai nói" được 412 video reuse' },
              { tag: 'Sub kèn brass', body: 'Drop-in tại 0:08 — thấy ở 28 hook video Tech' },
            ]}
          />
          <RailSection
            kicker="HÌNH THỨC HOT"
            title="Format"
            items={[
              { tag: '5 thứ ___', body: 'Listicle ngắn 30-45s · view TB +156%' },
              { tag: 'POV nghề', body: 'POV: Bạn là [nghề] · Edu &amp; Tech mạnh' },
              { tag: 'Reaction xé', body: 'Split screen reaction · giữ chân +22% retention' },
            ]}
          />
        </aside>
      </div>

      <style>{`
        @media (max-width: 1100px) {
          .trends-layout { grid-template-columns: 1fr !important; }
          .trends-rail { border-top: 1px solid var(--rule); }
          .trends-hero { grid-template-columns: 1fr !important; gap: 18px !important; }
        }
      `}</style>
    </div>
  );
}

function HeroStat({ label, value, delta }) {
  return (
    <div>
      <div className="mono uc" style={{ fontSize: 9, color: 'var(--ink-4)', marginBottom: 4 }}>{label}</div>
      <div className="tight" style={{ fontSize: 28, lineHeight: 1, color: 'var(--canvas)' }}>{value}</div>
      <div className="mono" style={{ fontSize: 10, color: 'var(--pos-deep)', marginTop: 4 }}>{delta}</div>
    </div>
  );
}

function SearchInput({ placeholder }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      padding: '6px 12px', border: '1px solid var(--rule)',
      borderRadius: 999, background: 'var(--paper)',
      width: 260,
    }}>
      <Icon name="search" size={13} style={{ color: 'var(--ink-4)' }} />
      <input placeholder={placeholder} style={{
        border: 0, outline: 0, background: 'transparent',
        fontSize: 12, flex: 1, color: 'var(--ink)',
      }} />
    </div>
  );
}

function Pill({ children, active }) {
  return (
    <button style={{
      padding: '6px 12px',
      border: '1px solid ' + (active ? 'var(--ink)' : 'var(--rule)'),
      borderRadius: 999,
      background: active ? 'var(--ink)' : 'var(--paper)',
      color: active ? 'var(--canvas)' : 'var(--ink-2)',
      fontSize: 11, fontWeight: 500,
    }}>{children}</button>
  );
}

function VideoGrid({ setRoute }) {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fill, minmax(190px, 1fr))',
      gap: 14,
    }}>
      {VIDEOS.map((v, i) => (
        <VideoTile key={v.id} v={v} setRoute={setRoute} index={i} />
      ))}
    </div>
  );
}

function VideoTile({ v, setRoute, index }) {
  return (
    <button onClick={() => setRoute('video')} className="tile" style={{ textAlign: 'left', display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{
        aspectRatio: '9/16', borderRadius: 8, overflow: 'hidden',
        background: v.bg, position: 'relative',
      }}>
        <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(180deg, transparent 40%, rgba(0,0,0,0.7))' }} />
        <div style={{
          position: 'absolute', top: 8, left: 8, display: 'flex', gap: 4,
        }}>
          {v.breakout && <span style={{ background: 'var(--accent)', color: 'white', padding: '2px 6px', borderRadius: 3, fontSize: 9, fontWeight: 700, letterSpacing: '0.05em' }}>BREAKOUT</span>}
          {v.viral && <span style={{ background: 'var(--accent-2)', color: 'var(--ink)', padding: '2px 6px', borderRadius: 3, fontSize: 9, fontWeight: 700, letterSpacing: '0.05em' }}>VIRAL</span>}
        </div>
        <div style={{
          position: 'absolute', bottom: 8, left: 10, right: 10,
          color: 'white',
        }}>
          <div className="mono" style={{ fontSize: 11, marginBottom: 2 }}>↑ {v.views}</div>
          <div style={{ fontSize: 12, lineHeight: 1.25, fontWeight: 500, overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>{v.title}</div>
        </div>
        <div style={{
          position: 'absolute', top: 8, right: 8,
          background: 'rgba(0,0,0,0.5)', color: 'white', padding: '2px 6px',
          borderRadius: 3, fontSize: 10, fontFamily: 'var(--mono)',
        }}>{v.dur}</div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span className="mono" style={{ fontSize: 10, color: 'var(--ink-3)' }}>{v.creator}</span>
        <span className="mono" style={{ fontSize: 10, color: 'var(--ink-4)' }}>{v.date}</span>
      </div>
      <div style={{
        fontSize: 11, color: 'var(--ink-3)',
        padding: '6px 10px', background: 'var(--paper)',
        border: '1px solid var(--rule)', borderRadius: 6,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <span>Phân tích →</span>
        <span className="mono" style={{ color: 'var(--ink-4)' }}>{v.niche}</span>
      </div>
    </button>
  );
}

function VideoList({ setRoute }) {
  return (
    <div className="card" style={{ overflow: 'hidden' }}>
      {VIDEOS.map((v, i) => (
        <button key={v.id} onClick={() => setRoute('video')} style={{
          display: 'grid', gridTemplateColumns: '60px 1fr 100px 100px 100px 80px',
          alignItems: 'center', gap: 14,
          padding: '12px 16px',
          borderBottom: i === VIDEOS.length - 1 ? 0 : '1px solid var(--rule)',
          textAlign: 'left', width: '100%',
        }}>
          <div style={{ aspectRatio: '9/16', height: 64, background: v.bg, borderRadius: 4 }} />
          <div>
            <div style={{ fontSize: 13, color: 'var(--ink)', marginBottom: 2 }}>{v.title}</div>
            <div className="mono" style={{ fontSize: 10, color: 'var(--ink-4)' }}>{v.creator} · {v.niche}</div>
          </div>
          <div className="mono" style={{ fontSize: 12, color: 'var(--ink-2)' }}>↑ {v.views}</div>
          <div className="tight" style={{ fontSize: 14, color: 'var(--ink-3)', fontStyle: 'italic' }}>"{v.hook}"</div>
          <div className="mono" style={{ fontSize: 11, color: 'var(--ink-4)' }}>{v.dur}</div>
          <div style={{ fontSize: 11, color: 'var(--pos-deep)' }}>Phân tích →</div>
        </button>
      ))}
    </div>
  );
}

function RailSection({ kicker, title, items }) {
  return (
    <div>
      <div className="mono uc" style={{ fontSize: 9, color: 'var(--ink-4)', marginBottom: 4 }}>{kicker}</div>
      <h3 className="tight" style={{ margin: 0, fontSize: 22, marginBottom: 12, paddingBottom: 10, borderBottom: '1px solid var(--ink)' }}>{title}</h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {items.map((it, i) => (
          <div key={i} style={{
            paddingBottom: 14,
            borderBottom: i === items.length - 1 ? 0 : '1px dashed var(--rule)',
          }}>
            <div className="mono uc" style={{
              fontSize: 9, color: it.accent ? 'var(--accent-deep)' : 'var(--ink-4)',
              marginBottom: 4,
            }}>
              {it.accent && <span style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: 'var(--accent)', marginRight: 6, verticalAlign: 'middle' }} />}
              {it.tag}
            </div>
            <div className="tight" style={{ fontSize: 14, lineHeight: 1.35, color: 'var(--ink-2)' }} dangerouslySetInnerHTML={{ __html: it.body }} />
          </div>
        ))}
      </div>
    </div>
  );
}

window.TrendsScreen = TrendsScreen;
