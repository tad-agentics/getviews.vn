// ============================================================
// Threaded research — follow-up turn renderers + session drawer.
// Appended to AnswerScreen to keep answer.jsx manageable.
// ============================================================

const { Icon, AnswerBlock, EvidenceCard, ActionCard, ResearchStep, EVIDENCE_VIDEOS } = window;

// ----- Turn divider: kicker + serif question + mini pulse -----
function TurnDivider({ index, q, kind, when = 'vừa xong' }) {
  const labels = {
    timing:   'THỜI ĐIỂM',
    creators: 'CREATOR SÂU',
    script:   'KỊCH BẢN',
    generic:  'ĐÀO SÂU',
  };
  return (
    <div style={{ marginTop: 56, paddingTop: 28, position: 'relative' }}>
      {/* node on the timeline rail */}
      <div className="turn-node" style={{
        position: 'absolute', left: -22, top: 30,
        width: 9, height: 9, borderRadius: '50%',
        background: 'var(--accent)', border: '2px solid var(--canvas)',
        boxShadow: '0 0 0 1px var(--ink)',
      }} />
      <div className="mono uc" style={{
        fontSize: 10, letterSpacing: '0.18em', color: 'var(--accent)',
        marginBottom: 10, display: 'flex', alignItems: 'center', gap: 10, fontWeight: 600,
      }}>
        <span>{labels[kind] || 'ĐÀO SÂU'} · LƯỢT {String(index + 1).padStart(2, '0')}</span>
        <span style={{ flex: 1, height: 1, background: 'var(--rule)' }} />
        <span style={{ color: 'var(--ink-4)' }}>{when}</span>
      </div>
      <h2 className="tight" style={{
        fontFamily: 'var(--serif)',
        fontSize: 'clamp(22px, 2.6vw, 30px)',
        lineHeight: 1.15, margin: 0,
        color: 'var(--ink)', letterSpacing: '-0.02em',
        fontWeight: 500, textWrap: 'balance',
      }}>
        {q}
      </h2>
      <MiniResearch />
    </div>
  );
}

function MiniResearch() {
  const [stage, setStage] = React.useState(0);
  React.useEffect(() => {
    if (stage >= 2) return;
    const t = setTimeout(() => setStage(s => s + 1), [500, 600][stage]);
    return () => clearTimeout(t);
  }, [stage]);
  const done = stage >= 2;
  return (
    <div style={{ display: 'flex', gap: 14, marginTop: 14, alignItems: 'center', flexWrap: 'wrap' }}>
      <ResearchStep label="Dùng lại 47 nguồn" done={stage >= 1} active={stage === 0} />
      <ResearchStep label="Trả lời" done={stage >= 2} active={stage === 1} />
      {done && (
        <span className="chip mono" style={{ fontSize: 10 }}>
          <Icon name="check" size={10} style={{ color: 'rgb(0, 159, 250)' }} />
          2.1s · cùng phiên
        </span>
      )}
    </div>
  );
}

// ----- Turn dispatch -----
function ContinuationTurn({ turn, index, setRoute }) {
  const Renderer = {
    timing:   TimingTurn,
    creators: CreatorsTurn,
    script:   ScriptTurn,
    generic:  GenericTurn,
  }[turn.kind] || GenericTurn;
  return (
    <div id={'turn-' + turn.id}>
      <TurnDivider index={index} q={turn.q} kind={turn.kind} />
      <Renderer q={turn.q} setRoute={setRoute} />
    </div>
  );
}

// ============================================================
// TIMING turn — heatmap + peak callouts
// ============================================================
function TimingTurn({ setRoute }) {
  // 7 days × 8 time buckets. Values 0–10 (synthetic).
  const days = ['T2','T3','T4','T5','T6','T7','CN'];
  const hours = ['6–9','9–12','12–15','15–18','18–20','20–22','22–24','0–3'];
  const data = [
    [1,3,4,5,8,9,6,2],
    [1,2,4,5,9,10,7,2],
    [1,3,5,6,8,9,7,3],
    [2,3,4,6,9,10,8,3],
    [2,3,5,7,9,10,8,4],
    [3,5,7,8,10,9,7,5],
    [4,6,7,8,9,7,5,4],
  ];
  const tone = v => {
    if (v >= 9) return 'var(--accent)';
    if (v >= 7) return 'var(--accent-soft)';
    if (v >= 5) return 'rgba(37, 244, 238, 0.25)';
    if (v >= 3) return 'var(--canvas-2)';
    return 'var(--paper)';
  };
  return (
    <div style={{ marginTop: 24, display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Headline + insight */}
      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 280px', gap: 24,
        padding: '18px 22px', border: '1px solid var(--ink)', background: 'var(--paper)',
      }} className="timing-head">
        <div>
          <div className="mono uc" style={{ fontSize: 10, letterSpacing: '0.16em', color: 'var(--ink-4)', marginBottom: 6 }}>SƯỚNG NHẤT</div>
          <div style={{ fontFamily: 'var(--serif)', fontSize: 32, lineHeight: 1.1, fontWeight: 500, letterSpacing: '-0.02em' }}>
            Thứ 7, 18:00 – 22:00
          </div>
          <div style={{ fontSize: 14, color: 'var(--ink-3)', marginTop: 8, lineHeight: 1.5, textWrap: 'pretty' }}>
            Post trong cửa sổ này được view gấp <strong style={{ color: 'var(--ink)' }}>2.8×</strong> trung bình ngách Tech. Thấp nhất: <span className="mono">3–6h</span> sáng T2.
          </div>
        </div>
        <div>
          <div className="mono uc" style={{ fontSize: 9, color: 'var(--ink-4)', marginBottom: 6 }}>3 CỬA SỔ CAO NHẤT</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {[
              { d: 'T7', h: '18–20', m: '10.0' },
              { d: 'T6', h: '20–22', m: '10.0' },
              { d: 'T5', h: '20–22', m: '10.0' },
            ].map((p, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
                <span className="mono" style={{ width: 20, color: 'var(--accent)', fontWeight: 600 }}>{String(i+1).padStart(2,'0')}</span>
                <span style={{ flex: 1 }}>{p.d} · {p.h}</span>
                <span className="mono" style={{ color: 'rgb(0, 159, 250)' }}>▲ {p.m}×</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Heatmap */}
      <div>
        <div className="mono uc" style={{ fontSize: 10, letterSpacing: '0.16em', color: 'var(--accent)', marginBottom: 10, fontWeight: 600 }}>
          HEATMAP · 7 NGÀY × 8 KHUNG GIỜ
        </div>
        <div style={{
          display: 'grid', gridTemplateColumns: '28px repeat(8, 1fr)', gap: 3,
          padding: 10, background: 'var(--paper)', border: '1px solid var(--rule)',
        }}>
          <div />
          {hours.map(h => (
            <div key={h} className="mono" style={{ fontSize: 9, color: 'var(--ink-4)', textAlign: 'center', padding: '2px 0' }}>{h}</div>
          ))}
          {days.map((d, di) => (
            <React.Fragment key={d}>
              <div className="mono" style={{ fontSize: 10, color: 'var(--ink-3)', display: 'flex', alignItems: 'center', fontWeight: 500 }}>{d}</div>
              {data[di].map((v, hi) => (
                <div key={hi} style={{
                  background: tone(v),
                  aspectRatio: '1.6 / 1',
                  border: v >= 9 ? '1px solid var(--accent-deep)' : '1px solid transparent',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 10, color: v >= 7 ? 'var(--ink)' : 'var(--ink-4)',
                  fontFamily: 'var(--mono)', fontWeight: v >= 7 ? 600 : 400,
                  transition: 'transform 0.15s',
                  cursor: 'pointer',
                }}>{v >= 5 ? v : ''}</div>
              ))}
            </React.Fragment>
          ))}
        </div>
        {/* Legend */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 10, fontSize: 10 }}>
          <span className="mono" style={{ color: 'var(--ink-4)' }}>THẤP</span>
          {[0,3,5,7,9].map(v => (
            <span key={v} style={{ width: 16, height: 12, background: tone(v), border: '1px solid var(--rule)' }} />
          ))}
          <span className="mono" style={{ color: 'var(--ink-4)' }}>CAO</span>
          <span style={{ flex: 1 }} />
          <span className="mono" style={{ color: 'var(--ink-4)' }}>Dữ liệu từ 47 video mẫu · niche Tech</span>
        </div>
      </div>

      {/* Inline follow-ups */}
      <TurnActions items={[
        { icon: 'script', title: 'Lên lịch post thử', sub: 'Schedule video tiếp theo vào khung 18–20 T7', onClick: () => setRoute('script'), primary: true },
        { icon: 'eye',    title: 'Xem kênh đối thủ',   sub: '@sammie.tech post 82% video trong cửa sổ này', onClick: () => setRoute('channel') },
      ]} />
    </div>
  );
}

// ============================================================
// CREATORS turn — 3 creator rows
// ============================================================
function CreatorsTurn({ setRoute }) {
  const rows = [
    { handle: '@sammie.tech',  name: 'Sammie Trần', followers: '412K', avg: '89K',  growth: '+34%', sample: 'Mình vừa test ChatGPT Pro và nó...', hits: '3/5', match: 94, bg: '#1F2A3B' },
    { handle: '@minhtuan.dev', name: 'Tuấn Minh',   followers: '278K', avg: '124K', growth: '+28%', sample: 'Mình vừa test con laptop 12tr này và…', hits: '4/6', match: 88, bg: '#3A2B4A' },
    { handle: '@linhgpt',      name: 'Linh GPT',    followers: '182K', avg: '76K',  growth: '+22%', sample: 'Không ai nói với bạn là Apple Intel…', hits: '2/4', match: 81, bg: '#2B3A38' },
  ];
  return (
    <div style={{ marginTop: 24, display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ padding: '16px 20px', border: '1px solid var(--ink)', background: 'var(--paper)' }}>
        <div className="mono uc" style={{ fontSize: 10, letterSpacing: '0.16em', color: 'var(--ink-4)', marginBottom: 6 }}>KẾT LUẬN</div>
        <div style={{ fontFamily: 'var(--serif)', fontSize: 22, lineHeight: 1.25, letterSpacing: '-0.01em', fontWeight: 500, textWrap: 'pretty' }}>
          <strong style={{ background: 'var(--accent-soft)', padding: '0 6px', borderRadius: 4 }}>3 creator</strong> đang khai thác pattern "Mình vừa test ___ và" thành công nhất — cộng lại chiếm 39% view của toàn nhóm video thắng.
        </div>
      </div>

      {rows.map((c, i) => (
        <div key={c.handle} style={{
          display: 'grid', gridTemplateColumns: '44px 1fr 140px 140px auto',
          gap: 16, alignItems: 'center',
          padding: '16px 20px', border: '1px solid var(--rule)', background: 'var(--paper)',
        }} className="creator-row">
          <div style={{
            width: 44, height: 44, borderRadius: '50%',
            background: c.bg, color: 'white',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontFamily: 'var(--serif)', fontSize: 18, fontWeight: 500, letterSpacing: '-0.02em',
          }}>{c.name[0]}</div>

          <div style={{ minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
              <span style={{ fontSize: 15, fontWeight: 500 }}>{c.name}</span>
              <span className="mono" style={{ fontSize: 11, color: 'var(--ink-4)' }}>{c.handle}</span>
              <span className="chip mono" style={{ fontSize: 9, padding: '2px 7px', background: 'var(--accent-soft)', color: 'var(--accent-deep)', border: '1px solid transparent' }}>
                {c.hits} video dùng hook này
              </span>
            </div>
            <div className="mono" style={{ fontSize: 12, color: 'var(--ink-3)', fontStyle: 'italic' }}>
              "{c.sample}"
            </div>
          </div>

          <div>
            <div className="mono uc" style={{ fontSize: 9, color: 'var(--ink-4)' }}>FOLLOW</div>
            <div className="mono" style={{ fontSize: 14, fontWeight: 500 }}>{c.followers}</div>
            <div className="mono" style={{ fontSize: 10, color: 'rgb(0, 159, 250)' }}>▲ {c.growth}</div>
          </div>

          <div>
            <div className="mono uc" style={{ fontSize: 9, color: 'var(--ink-4)' }}>VIEW TB</div>
            <div className="mono" style={{ fontSize: 14, fontWeight: 500 }}>{c.avg}</div>
            <div className="mono" style={{ fontSize: 10, color: 'var(--ink-4)' }}>match {c.match}%</div>
          </div>

          <button className="btn" onClick={() => setRoute('channel')} style={{ cursor: 'pointer', fontSize: 12 }}>
            Phân tích sâu <Icon name="arrow-right" size={11} />
          </button>
        </div>
      ))}

      <TurnActions items={[
        { icon: 'users', title: 'Tìm thêm creator khớp', sub: 'Tiêu chí: Tech · 100K–500K · dùng hook #1', onClick: () => setRoute('kol'), primary: true },
        { icon: 'trend', title: 'So sánh 3 creator', sub: 'Growth · engagement · pattern chung', onClick: () => setRoute('channel') },
      ]} />

      <style>{`
        @media (max-width: 900px) {
          .creator-row { grid-template-columns: 44px 1fr !important; }
          .creator-row > div:nth-child(3), .creator-row > div:nth-child(4), .creator-row > button { display: none !important; }
        }
      `}</style>
    </div>
  );
}

// ============================================================
// SCRIPT turn — 30s script timeline
// ============================================================
function ScriptTurn({ setRoute }) {
  const beats = [
    { t: '0.0 – 1.2s', tag: 'HOOK',    line: 'Mình vừa test ChatGPT Pro và…',                                         note: 'Cắt ngay giữa câu. Không dừng ở "và".' },
    { t: '1.2 – 3.0s', tag: 'CÂU MÓC', line: '…ba tính năng mà 80% người không biết đến.',                               note: 'Đặt con số + promise cụ thể.' },
    { t: '3 – 12s',    tag: 'MỤC 1',   line: 'Deep Research — cho nó 1 câu hỏi, 15 phút sau có báo cáo 8 trang.',          note: 'Show màn hình. Speed x2.' },
    { t: '12 – 20s',   tag: 'MỤC 2',   line: 'Custom GPT — làm bot riêng trong 3 phút, không cần code.',                   note: 'Cut nhanh. Show kết quả trước.' },
    { t: '20 – 26s',   tag: 'MỤC 3',   line: 'Voice — nói chuyện như người thật. Ngắt lời được.',                          note: 'Ghi 1 cuộc hội thoại thực.' },
    { t: '26 – 30s',   tag: 'CTA',     line: 'Bạn đã thử cái nào chưa? Comment cho mình biết.',                             note: 'Hỏi ngược, KHÔNG nói "follow".' },
  ];
  return (
    <div style={{ marginTop: 24, display: 'flex', flexDirection: 'column', gap: 18 }}>
      {/* Header meta */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
        border: '1px solid var(--ink)', background: 'var(--paper)',
      }} className="script-meta">
        {[
          ['NGÁCH', 'Tech'],
          ['HOOK', '"Mình vừa test ___ và"'],
          ['THỜI LƯỢNG', '30s'],
          ['DỰ KIẾN VIEW', '180–260K'],
        ].map(([k, v], i) => (
          <div key={k} style={{ padding: '12px 16px', borderLeft: i > 0 ? '1px solid var(--rule)' : 'none' }}>
            <div className="mono uc" style={{ fontSize: 9, color: 'var(--ink-4)', letterSpacing: '0.14em' }}>{k}</div>
            <div style={{ fontSize: 15, fontWeight: 500, marginTop: 4, textWrap: 'balance' }}>{v}</div>
          </div>
        ))}
      </div>

      {/* Timeline bar */}
      <div style={{ position: 'relative', height: 32, border: '1px solid var(--ink)', display: 'flex', overflow: 'hidden' }}>
        {beats.map((b, i) => {
          const colors = ['var(--accent)', 'var(--accent-deep)', 'var(--ink-2)', 'var(--ink-3)', 'var(--ink-4)', 'var(--accent-2-deep)'];
          const widths = [4, 6, 30, 27, 20, 13];
          return (
            <div key={i} style={{
              flex: widths[i], background: colors[i],
              borderRight: i < beats.length - 1 ? '1px solid var(--canvas)' : 'none',
              display: 'flex', alignItems: 'center', padding: '0 8px',
              color: i < 2 ? 'white' : 'var(--canvas)', fontSize: 10, fontFamily: 'var(--mono)', fontWeight: 600,
            }}>{b.tag}</div>
          );
        })}
      </div>

      {/* Beats */}
      <div style={{ display: 'flex', flexDirection: 'column', border: '1px solid var(--rule)', background: 'var(--paper)' }}>
        {beats.map((b, i) => (
          <div key={i} style={{
            display: 'grid', gridTemplateColumns: '90px 56px 1fr 240px', gap: 14,
            padding: '14px 16px', borderTop: i > 0 ? '1px solid var(--rule)' : 'none',
            alignItems: 'start',
          }} className="script-beat">
            <div className="mono" style={{ fontSize: 11, color: 'var(--ink-4)', paddingTop: 2 }}>{b.t}</div>
            <span className="mono" style={{
              fontSize: 9, letterSpacing: '0.1em', padding: '3px 7px', borderRadius: 3,
              background: i < 2 ? 'var(--accent)' : i === 5 ? 'var(--accent-2-deep)' : 'var(--ink)',
              color: i < 2 || i === 5 ? 'white' : 'var(--canvas)',
              alignSelf: 'start', height: 18, display: 'flex', alignItems: 'center', fontWeight: 600,
            }}>{b.tag}</span>
            <div style={{ fontSize: 15, lineHeight: 1.5, textWrap: 'pretty', color: 'var(--ink)' }}>
              {b.line}
            </div>
            <div style={{ fontSize: 12, color: 'var(--ink-3)', fontStyle: 'italic', lineHeight: 1.45 }}>
              {b.note}
            </div>
          </div>
        ))}
      </div>

      <TurnActions items={[
        { icon: 'script', title: 'Mở trong Xưởng Viết', sub: 'Chỉnh sửa, xuất voice-over, lên kế hoạch quay', onClick: () => setRoute('script'), primary: true },
        { icon: 'copy',   title: 'Copy script', sub: 'Dán vào editor hoặc CapCut' },
        { icon: 'download', title: 'Export PDF', sub: 'Gửi cho team quay' },
      ]} />

      <style>{`
        @media (max-width: 900px) {
          .script-meta { grid-template-columns: 1fr 1fr !important; }
          .script-beat { grid-template-columns: 70px 1fr !important; gap: 8px !important; }
          .script-beat > span, .script-beat > div:last-child { grid-column: 2 !important; }
        }
      `}</style>
    </div>
  );
}

// ============================================================
// GENERIC turn — narrative + evidence cards
// ============================================================
function GenericTurn({ q, setRoute }) {
  return (
    <div style={{ marginTop: 24, display: 'flex', flexDirection: 'column', gap: 18 }}>
      <div style={{ padding: '20px 22px', border: '1px solid var(--ink)', background: 'var(--paper)' }}>
        <div className="mono uc" style={{ fontSize: 10, letterSpacing: '0.16em', color: 'var(--ink-4)', marginBottom: 8 }}>TRẢ LỜI</div>
        <p style={{
          margin: 0, fontFamily: 'var(--serif)', fontSize: 20, lineHeight: 1.45,
          letterSpacing: '-0.01em', textWrap: 'pretty',
        }}>
          Dựa trên 47 video mẫu: <strong style={{ background: 'var(--accent-soft)', padding: '0 6px', borderRadius: 4, fontFamily: 'var(--sans)', fontWeight: 600 }}>có</strong> — pattern này hoạt động tốt hơn trong các video listicle ngắn (25–40s) với sound gốc. <span style={{ color: 'var(--ink-3)' }}>Dưới đây là 3 ví dụ gần nhất.</span>
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14 }} className="generic-grid">
        {EVIDENCE_VIDEOS.slice(0, 3).map((v, i) => (
          <EvidenceCard key={v.id} video={v} idx={i + 1} onOpen={() => setRoute('video')} />
        ))}
      </div>

      <style>{`
        @media (max-width: 720px) { .generic-grid { grid-template-columns: 1fr !important; } }
      `}</style>
    </div>
  );
}

// ----- Shared inline action row (below any continuation turn) -----
function TurnActions({ items }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: `repeat(${items.length}, 1fr)`, gap: 10, marginTop: 8 }} className="turn-actions">
      {items.map((a, i) => (
        <ActionCard key={i} icon={a.icon} title={a.title} sub={a.sub} cta={a.primary ? 'Bắt đầu' : 'Mở'} onClick={a.onClick} primary={a.primary} />
      ))}
      <style>{`
        @media (max-width: 900px) { .turn-actions { grid-template-columns: 1fr !important; } }
      `}</style>
    </div>
  );
}

// ============================================================
// Session drawer — list of past research sessions
// ============================================================
function SessionDrawer({ open, onClose }) {
  if (!open) return null;
  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 100,
      background: 'rgba(10, 12, 16, 0.35)',
    }} onClick={onClose}>
      <aside onClick={e => e.stopPropagation()} style={{
        position: 'absolute', left: 0, top: 0, bottom: 0, width: 380,
        background: 'var(--canvas)', borderRight: '1px solid var(--ink)',
        display: 'flex', flexDirection: 'column',
        animation: 'slideIn 0.25s ease-out',
      }}>
        <div style={{
          padding: '20px 22px 16px', borderBottom: '1px solid var(--rule)',
          display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 10,
        }}>
          <div>
            <div className="mono uc" style={{ fontSize: 10, letterSpacing: '0.18em', color: 'var(--ink-4)', marginBottom: 4 }}>PHIÊN NGHIÊN CỨU</div>
            <div style={{ fontFamily: 'var(--serif)', fontSize: 22, lineHeight: 1.1, fontWeight: 500, letterSpacing: '-0.02em' }}>Các phiên gần đây</div>
          </div>
          <button className="chip" onClick={onClose} style={{ cursor: 'pointer' }}>Đóng ✕</button>
        </div>

        <button className="btn btn-accent" style={{
          margin: '16px 22px', padding: '12px 14px', justifyContent: 'center', cursor: 'pointer', fontSize: 13,
        }}>
          <Icon name="sparkle" size={12} /> Phiên mới
        </button>

        <div style={{ flex: 1, overflow: 'auto', padding: '0 10px 20px' }}>
          {PAST_SESSIONS.map(s => (
            <button key={s.id} style={{
              width: '100%', textAlign: 'left', cursor: 'pointer',
              background: s.active ? 'var(--accent-soft)' : 'transparent',
              border: 0, borderLeft: s.active ? '3px solid var(--accent)' : '3px solid transparent',
              padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 4,
              borderRadius: 0,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: 'var(--ink-4)' }}>
                <span className="mono uc" style={{ fontSize: 9, letterSpacing: '0.14em', color: s.active ? 'var(--accent-deep)' : 'var(--ink-4)' }}>{s.niche}</span>
                <span>·</span>
                <span>{s.turns} lượt</span>
                <span style={{ flex: 1 }} />
                <span className="mono">{s.when}</span>
              </div>
              <div style={{
                fontSize: 14, fontWeight: s.active ? 500 : 400,
                color: 'var(--ink)', lineHeight: 1.3, textWrap: 'pretty',
              }}>
                {s.title}
              </div>
            </button>
          ))}
        </div>

        <div style={{ padding: '12px 22px', borderTop: '1px solid var(--rule)', fontSize: 11, color: 'var(--ink-4)', display: 'flex', justifyContent: 'space-between' }}>
          <span className="mono">{PAST_SESSIONS.length} phiên · 30 ngày</span>
          <button className="chip" style={{ cursor: 'pointer' }}>Xem tất cả</button>
        </div>

        <style>{`@keyframes slideIn { from { transform: translateX(-100%); } to { transform: none; } }`}</style>
      </aside>
    </div>
  );
}

window.ContinuationTurn = ContinuationTurn;
window.SessionDrawer = SessionDrawer;
