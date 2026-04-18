// ============================================================
// KOL / Creator finder
// ============================================================

function KolScreen({ setRoute }) {
  const [tab, setTab] = React.useState('pinned');
  const [picked, setPicked] = React.useState(CREATORS[0].handle);
  const focused = CREATORS.find(c => c.handle === picked) || CREATORS[0];

  // Pinned = first 3 creators (fake), the rest are "discover"
  const pinnedHandles = [CREATORS[0].handle, CREATORS[1].handle, CREATORS[2].handle];
  const visibleList = tab === 'pinned'
    ? CREATORS.filter(c => pinnedHandles.includes(c.handle))
    : CREATORS;

  return (
    <div style={{ background: 'var(--canvas)', minHeight: '100%' }}>
      <div style={{ maxWidth: 1320, margin: '0 auto', padding: '24px 28px 80px' }}>

        {/* Tab bar for pinned vs discover */}
        <div style={{
            display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between',
            gap: 20, flexWrap: 'wrap', marginBottom: 18, paddingBottom: 14,
            borderBottom: '1px solid var(--rule)',
          }}>
            <div>
              <div className="mono uc" style={{ fontSize: 10, letterSpacing: '0.16em', color: 'var(--ink-4)', marginBottom: 6 }}>
                KÊNH THAM CHIẾU · NGÁCH TECH
              </div>
              <h1 className="tight" style={{
                margin: 0, fontSize: 'clamp(28px, 3.2vw, 40px)', lineHeight: 1.05,
                letterSpacing: '-0.02em', fontWeight: 600, maxWidth: 640,
              }}>
                {tab === 'pinned'
                  ? <>3 kênh bạn đang <em style={{ color: 'var(--accent)', fontStyle: 'italic' }}>theo dõi sát</em></>
                  : <>Khám phá <em style={{ color: 'var(--accent)', fontStyle: 'italic' }}>kênh mới</em> trong ngách</>}
              </h1>
            </div>
            <div style={{ display: 'flex', gap: 0, border: '1px solid var(--ink)', borderRadius: 6, overflow: 'hidden' }}>
              {[
                ['pinned',   'Đang theo dõi', pinnedHandles.length, 'bookmark'],
                ['discover', 'Khám phá',      CREATORS.length,       'sparkle'],
              ].map(([k, lbl, n, ic]) => (
                <button key={k} onClick={() => setTab(k)} style={{
                  padding: '10px 16px', display: 'flex', alignItems: 'center', gap: 8,
                  background: tab === k ? 'var(--ink)' : 'transparent',
                  color: tab === k ? 'var(--canvas)' : 'var(--ink)',
                  fontSize: 13, fontWeight: 500, cursor: 'pointer',
                }}>
                  <Icon name={ic} size={12} />
                  <span>{lbl}</span>
                  <span className="mono" style={{
                    fontSize: 10, padding: '2px 6px', borderRadius: 4,
                    background: tab === k ? 'rgba(255,255,255,0.18)' : 'var(--canvas-2)',
                    color: tab === k ? 'var(--canvas)' : 'var(--ink-4)',
                  }}>{n}</span>
                </button>
              ))}
            </div>
        </div>

        {/* Filter ribbon */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '8px 0 18px', gap: 16, flexWrap: 'wrap',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            <span className="mono uc" style={{ fontSize: 9, color: 'var(--ink-4)' }}>LỌC THEO</span>
            <Pill active>Tech</Pill>
            <Pill>100K–1M</Pill>
            <Pill>Việt Nam</Pill>
            <Pill>Tăng trưởng nhanh</Pill>
            <Pill>+ Thêm điều kiện</Pill>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <SearchInput placeholder="Tìm @handle…" />
            {tab === 'pinned' && (
              <button className="btn"><Icon name="plus" size={12} /> Ghim kênh</button>
            )}
            {tab === 'discover' && (
              <button className="btn"><Icon name="sparkle" size={12} /> Gợi ý cho ngách của tôi</button>
            )}
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: 28 }} className="kol-layout">
          {/* List */}
          <div>
            <div style={{
              display: 'grid', gridTemplateColumns: '40px 2fr 100px 100px 100px 80px',
              padding: '10px 18px',
              borderBottom: '1px solid var(--ink)', background: 'transparent',
            }}>
              {['#', 'CREATOR', 'FOLLOW', 'VIEW TB', 'TĂNG 30D', 'MATCH'].map(h => (
                <div key={h} className="mono uc" style={{ fontSize: 9, color: 'var(--ink-4)' }}>{h}</div>
              ))}
            </div>
            {visibleList.map((c, i) => {
              const isPinned = pinnedHandles.includes(c.handle);
              return (
              <button key={c.handle} onClick={() => setPicked(c.handle)} style={{
                display: 'grid', gridTemplateColumns: '40px 2fr 100px 100px 100px 80px',
                padding: '14px 18px', alignItems: 'center',
                borderBottom: '1px solid var(--rule)',
                background: picked === c.handle ? 'var(--paper)' : 'transparent',
                width: '100%', textAlign: 'left',
                cursor: 'pointer',
              }}>
                <div className="mono" style={{ fontSize: 11, color: 'var(--ink-4)' }}>0{i+1}</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{
                    width: 36, height: 36, borderRadius: '50%',
    background: ['var(--accent)', '#3D2F4A', '#2A3A5C', '#1F3A5C', '#4A2A5C', '#5C2A3A'][i % 6],
                    color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 16,
                  }}>{c.name.charAt(0)}</div>
                  <div>
                    <div style={{ fontSize: 13, color: 'var(--ink)', display: 'flex', alignItems: 'center', gap: 6 }}>
                      {c.name}
                      {isPinned && tab === 'discover' && (
                        <span className="mono uc" style={{
                          fontSize: 8, padding: '1px 5px', borderRadius: 3,
                          background: 'var(--accent-soft)', color: 'var(--accent-deep)',
                          letterSpacing: '0.1em', fontWeight: 700,
                        }}>GHIM</span>
                      )}
                    </div>
                    <div className="mono" style={{ fontSize: 10, color: 'var(--ink-4)' }}>{c.handle} · {c.tone}</div>
                  </div>
                </div>
                <div className="mono" style={{ fontSize: 12 }}>{c.followers}</div>
                <div className="mono" style={{ fontSize: 12 }}>{c.avg}</div>
                <div className="mono" style={{ fontSize: 12, color: 'var(--pos-deep)', fontWeight: 600 }}>{c.growth}</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div style={{
                    flex: 1, height: 4, borderRadius: 999, background: 'var(--rule)',
                    overflow: 'hidden',
                  }}>
                    <div style={{ width: `${c.match}%`, height: '100%', background: 'var(--accent)' }} />
                  </div>
                  <span className="mono" style={{ fontSize: 10, width: 22, textAlign: 'right' }}>{c.match}</span>
                </div>
              </button>
              );
            })}
          </div>

          {/* Detail card */}
          <aside>
            <div className="card" style={{ padding: 22, position: 'sticky', top: 86 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 14 }}>
                <div style={{
                  width: 56, height: 56, borderRadius: '50%',
                  background: 'var(--accent)', color: 'white',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 22,
                }}>{focused.name.charAt(0)}</div>
                <div>
                  <div className="tight" style={{ fontSize: 22, lineHeight: 1.05 }}>{focused.name}</div>
                  <div className="mono" style={{ fontSize: 11, color: 'var(--ink-3)' }}>{focused.handle}</div>
                </div>
              </div>

              <div style={{
                background: 'var(--canvas-2)', borderRadius: 8, padding: 14,
                display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 16,
              }}>
                <div>
                  <div className="mono uc" style={{ fontSize: 9, color: 'var(--ink-4)' }}>NGÁCH</div>
                  <div style={{ fontSize: 13, marginTop: 2 }}>{focused.niche}</div>
                </div>
                <div>
                  <div className="mono uc" style={{ fontSize: 9, color: 'var(--ink-4)' }}>FOLLOW</div>
                  <div style={{ fontSize: 13, marginTop: 2 }}>{focused.followers}</div>
                </div>
                <div>
                  <div className="mono uc" style={{ fontSize: 9, color: 'var(--ink-4)' }}>VIEW TB</div>
                  <div style={{ fontSize: 13, marginTop: 2 }}>{focused.avg}</div>
                </div>
                <div>
                  <div className="mono uc" style={{ fontSize: 9, color: 'var(--ink-4)' }}>TĂNG 30D</div>
                  <div style={{ fontSize: 13, marginTop: 2, color: 'var(--pos-deep)' }}>{focused.growth}</div>
                </div>
              </div>

              <div style={{ marginBottom: 14 }}>
                <div className="mono uc" style={{ fontSize: 9, color: 'var(--ink-4)', marginBottom: 6 }}>ĐỘ KHỚP NGÁCH BẠN</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div className="tight" style={{ fontSize: 36, color: 'var(--accent)' }}>{focused.match}<span style={{ fontSize: 16, color: 'var(--ink-4)' }}>/100</span></div>
                  <div style={{ fontSize: 11, color: 'var(--ink-3)', flex: 1 }}>
                    Cùng audience overlap, khác giọng — bổ sung tốt cho catalog của bạn.
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <button className="btn" onClick={() => setRoute('channel')}>
                  <Icon name="eye" size={12} /> Phân tích kênh đầy đủ
                </button>
                <button className="btn btn-ghost"><Icon name="bookmark" size={12} /> {pinnedHandles.includes(focused.handle) ? 'Bỏ ghim khỏi theo dõi' : 'Ghim để theo dõi'}</button>
                <button className="btn btn-ghost" onClick={() => setRoute('script')}><Icon name="script" size={12} /> Học hook từ kênh này</button>
              </div>
            </div>
          </aside>
        </div>
      </div>

      <style>{`
        @media (max-width: 1100px) {
          .kol-layout { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </div>
  );
}

window.KolScreen = KolScreen;
