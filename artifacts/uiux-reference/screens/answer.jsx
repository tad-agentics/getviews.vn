// ============================================================
// AnswerScreen — threaded research session.
// Turn 0 = primary brief. Turn N+ = follow-up deep-dives (timing /
// creators / script / generic). Left drawer lists past sessions.
// ============================================================

// --- Past session mock list (for drawer) ---
const PAST_SESSIONS = [
  { id: 's-now',  title: 'Hook nào đang hot trong Tech?',    niche: 'Tech',   turns: 1, when: 'Vừa xong', active: true  },
  { id: 's-1',    title: 'Đối thủ @sammie.tech tuần này',    niche: 'Tech',   turns: 3, when: 'Hôm qua',  active: false },
  { id: 's-2',    title: 'Thời điểm đăng tốt nhất cho Beauty', niche: 'Beauty', turns: 2, when: '2 ngày',   active: false },
  { id: 's-3',    title: 'Gaming · pattern 30s ngắn',        niche: 'Gaming', turns: 5, when: '3 ngày',   active: false },
  { id: 's-4',    title: 'KOL Tech < 500K, tăng nhanh',      niche: 'Tech',   turns: 2, when: 'Tuần trước', active: false },
  { id: 's-5',    title: 'Food · viral hooks April',         niche: 'Food',   turns: 4, when: '12 ngày',  active: false },
];

// Classify a follow-up query into a specialized turn shape
function classifyQuery(q) {
  const s = (q || '').toLowerCase();
  if (/thời\s*điểm|giờ|khi\s*nào|đăng|post/.test(s)) return 'timing';
  if (/creator|kol|kênh|@|ai\s*dùng|ai\s*đang/.test(s)) return 'creators';
  if (/kịch\s*bản|script|viết|tạo.*video/.test(s)) return 'script';
  return 'generic';
}

function AnswerScreen({ setRoute }) {
  const ContinuationTurn = window.ContinuationTurn;
  const SessionDrawer = window.SessionDrawer;
  const seedQ = (typeof window !== 'undefined' && window.__gvQuery) ||
            'Hook nào đang hiệu quả nhất trong ngách Công nghệ tuần này?';
  const niche = (typeof window !== 'undefined' && window.__gvNiche) || 'Tech';

  const [turns, setTurns] = React.useState([{ id: 't0', kind: 'primary', q: seedQ }]);
  const [drawerOpen, setDrawerOpen] = React.useState(false);

  // Primary brief research stages
  const [stage, setStage] = React.useState(0);
  React.useEffect(() => {
    if (stage >= 4) return;
    const t = setTimeout(() => setStage(s => s + 1), [600, 700, 800, 500][stage]);
    return () => clearTimeout(t);
  }, [stage]);
  const primaryDone = stage >= 4;

  const appendTurn = (q) => {
    const kind = classifyQuery(q);
    const id = 't' + (turns.length);
    setTurns(ts => [...ts, { id, kind, q }]);
    // Scroll to new turn after render
    setTimeout(() => {
      const el = document.getElementById('turn-' + id);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 50);
  };

  return (
    <div style={{ background: 'var(--canvas)', minHeight: '100%', position: 'relative' }}>
      <SessionDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />

      <div style={{ maxWidth: 1320, margin: '0 auto', padding: '28px 28px 120px' }}>

        {/* Back + breadcrumb + drawer toggle */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 18, fontSize: 12, color: 'var(--ink-4)', flexWrap: 'wrap' }}>
          <button className="chip" onClick={() => setRoute('home')} style={{ cursor: 'pointer' }}>
            <Icon name="arrow-left" size={11} /> Studio
          </button>
          <button className="chip" onClick={() => setDrawerOpen(true)} style={{ cursor: 'pointer' }}>
            <Icon name="list" size={11} /> Phiên nghiên cứu <span className="mono" style={{ color: 'var(--ink-4)' }}>· {PAST_SESSIONS.length}</span>
          </button>
          <span className="mono">/</span>
          <span className="mono uc" style={{ fontSize: 10, letterSpacing: '0.14em' }}>NGHIÊN CỨU · {niche.toUpperCase()}</span>
          <span style={{ flex: 1 }} />
          <ProgressPill done={primaryDone} stage={stage} />
        </div>

        {/* Session title header */}
        <QueryHeader q={seedQ} niche={niche} stage={stage} done={primaryDone} />

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 1fr) 320px',
          gap: 40,
          marginTop: 36,
          alignItems: 'start',
        }} className="answer-grid">

          {/* MAIN STREAM — all turns */}
          <div style={{ position: 'relative' }}>
            {/* Timeline rail linking turns */}
            {turns.length > 1 && (
              <div style={{
                position: 'absolute', left: -18, top: 20, bottom: 100,
                width: 1, background: 'var(--rule)',
              }} className="turn-rail" />
            )}

            {/* TURN 0 — Primary brief */}
            <div id="turn-t0">

            {/* TL;DR */}
            <AnswerBlock
              kicker="TÓM TẮT"
              title="Điều bạn nên biết"
              show={stage >= 2}
              delay={0}
            >
              <p className="lead" style={{
                fontSize: 22, lineHeight: 1.45, margin: 0,
                fontFamily: 'var(--serif)', color: 'var(--ink)',
                letterSpacing: '-0.01em',
                textWrap: 'pretty',
              }}>
                Ba hook đang <em style={{ color: 'var(--accent)', fontStyle: 'italic' }}>bùng nổ</em> trong ngách
                Công nghệ tuần này — tất cả đều là <strong style={{ fontFamily: 'var(--sans)', fontWeight: 600, background: 'var(--accent-soft)', padding: '0 6px', borderRadius: 4 }}>câu hỏi đảo ngược kỳ vọng</strong>, đặt trong 1.2 giây đầu. Hook <span className="mono" style={{ background: 'var(--ink)', color: 'var(--canvas)', padding: '1px 6px', borderRadius: 3, fontSize: 16 }}>"Mình vừa test ___ và"</span> đang dẫn đầu với retention 74% — cao hơn mức trung bình ngách 2.3×.
              </p>

              <div style={{
                display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 0,
                marginTop: 24, borderTop: '1px solid var(--ink)', borderBottom: '1px solid var(--ink)',
              }}>
                <SumStat label="hook đang nổ" value="3" trend="+3 tuần này" tone="up" />
                <SumStat label="retention TB" value="74%" trend="gấp 2.3× ngách" tone="up" border />
                <SumStat label="video mẫu" value="47" trend="từ 14 kênh" />
              </div>
            </AnswerBlock>

            {/* Evidence — hooks breakdown */}
            <AnswerBlock
              kicker="BẰNG CHỨNG · 3 HOOK"
              title="Pattern đang thắng, xếp theo retention"
              show={stage >= 3}
              delay={120}
            >
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                <HookFinding
                  rank={1}
                  pattern="Mình vừa test ___ và"
                  retention="74%"
                  delta="+312%"
                  uses={214}
                  insight="Câu mở đầu nêu một hành động cụ thể + cắt ngang — tạo cảm giác 'xem lén'. Hiệu quả nhất khi ___ là sản phẩm người xem đang cân nhắc."
                  videos={[0, 1]}
                />
                <HookFinding
                  rank={2}
                  pattern="Không ai nói với bạn là ___"
                  retention="68%"
                  delta="+248%"
                  uses={186}
                  insight="Tín hiệu 'bí mật ngành'. Cao điểm với video 25–40 giây, giảm hiệu quả khi dài hơn 60s."
                  videos={[2, 3]}
                />
                <HookFinding
                  rank={3}
                  pattern="Lướt thấy ___ mà không thể tin"
                  retention="61%"
                  delta="+182%"
                  uses={152}
                  insight="Phản ứng-first. Tốt khi ___ là screenshot/screen recording — người xem tự diễn giải."
                  videos={[4, 5]}
                />
              </div>
            </AnswerBlock>

            {/* Inline evidence: Top videos */}
            <AnswerBlock
              kicker="VIDEO MẪU"
              title="6 video dùng pattern này đang bùng nổ"
              show={stage >= 3}
              delay={180}
              action={<button className="chip" onClick={() => setRoute('trends')}>Xem tất cả 47 <Icon name="arrow-right" size={11} /></button>}
            >
              <div style={{
                display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14,
              }} className="video-evidence-grid">
                {EVIDENCE_VIDEOS.map((v, i) => (
                  <EvidenceCard key={v.id} video={v} idx={i + 1} onOpen={() => setRoute('video')} />
                ))}
              </div>
            </AnswerBlock>

            {/* Pattern findings — data viz */}
            <AnswerBlock
              kicker="PATTERNS"
              title="Điểm chung của 47 video thắng"
              show={stage >= 3}
              delay={240}
            >
              <div style={{
                display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 0,
                border: '1px solid var(--ink)',
              }} className="patterns-grid">
                <PatternCell
                  title="Thời lượng vàng"
                  finding="25–40 giây"
                  detail="71% video thắng nằm trong khoảng này. Video > 60s giảm retention 34%."
                  chart={<DurationChart />}
                />
                <PatternCell
                  title="Thời điểm hook"
                  finding="0.8 – 1.4s"
                  detail="Hook đặt trước giây thứ 2 có retention cao hơn 1.8×. Sau giây 3: drop-off tăng vọt."
                  chart={<HookTimingChart />}
                  leftBorder
                />
                <PatternCell
                  title="Nhạc nền"
                  finding="Sound gốc thắng"
                  detail="62% dùng sound gốc (không phải trending audio). CTR comment cao hơn 2.1×."
                  chart={<SoundMix />}
                  topBorder
                />
                <PatternCell
                  title="CTA"
                  finding="Hỏi ngược, không 'follow'"
                  detail="CTA dạng câu hỏi (‘Bạn thấy sao?’) ăn gấp 3.4× lần ‘follow để xem thêm’."
                  chart={<CtaBars />}
                  leftBorder
                  topBorder
                />
              </div>
            </AnswerBlock>

            {/* Action blocks */}
            <AnswerBlock
              kicker="BƯỚC TIẾP THEO"
              title="Biến insight thành video"
              show={stage >= 4}
              delay={0}
            >
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }} className="action-grid">
                <ActionCard
                  icon="script"
                  title="Tạo kịch bản từ hook #1"
                  sub="Dùng pattern &quot;Mình vừa test ___ và&quot; cho video sắp tới của bạn"
                  cta="Mở Xưởng Viết"
                  onClick={() => setRoute('script')}
                  primary
                />
                <ActionCard
                  icon="eye"
                  title="Phân tích sâu @sammie.tech"
                  sub="Creator dùng pattern này thành công nhất — 3/5 video gần nhất"
                  cta="Xem kênh"
                  onClick={() => setRoute('channel')}
                />
                <ActionCard
                  icon="trend"
                  title="Theo dõi trend"
                  sub="Nhận alert khi có pattern mới xuất hiện trong ngách Tech"
                  cta="Bật cảnh báo"
                />
              </div>
            </AnswerBlock>
            </div>

            {/* Continuation turns */}
            {turns.slice(1).map((t, i) => (
              <ContinuationTurn key={t.id} turn={t} index={i + 1} setRoute={setRoute} />
            ))}

            {/* Follow-up composer */}
            {primaryDone && <FollowUpComposer setRoute={setRoute} onSubmit={appendTurn} />}
          </div>

          {/* RIGHT RAIL */}
          <aside className="answer-rail">
            <Sources stage={stage} />
            <RelatedQs setRoute={setRoute} onPick={appendTurn} />
            <SaveCard />
          </aside>

        </div>
      </div>

      <style>{`
        @media (max-width: 1100px) {
          .answer-grid { grid-template-columns: 1fr !important; }
          .answer-rail { order: -1; }
          .video-evidence-grid { grid-template-columns: repeat(2, 1fr) !important; }
          .patterns-grid { grid-template-columns: 1fr !important; }
          .action-grid { grid-template-columns: 1fr !important; }
          .turn-rail { display: none; }
        }
        @media (max-width: 720px) {
          .video-evidence-grid { grid-template-columns: 1fr !important; }
        }
        .answer-block { opacity: 0; transform: translateY(14px); transition: opacity 0.5s, transform 0.5s; }
        .answer-block.show { opacity: 1; transform: none; }
      `}</style>
    </div>
  );
}

// ============================================================
// Query header — the question, the context, the research pulse
// ============================================================

function QueryHeader({ q, niche, stage, done }) {
  return (
    <div style={{
      borderTop: '2px solid var(--ink)',
      borderBottom: '1px solid var(--rule)',
      padding: '24px 0 22px',
    }}>
      <div className="mono uc" style={{
        fontSize: 10, letterSpacing: '0.16em', color: 'var(--ink-4)', marginBottom: 12,
        display: 'flex', alignItems: 'center', gap: 10,
      }}>
        <span>CÂU HỎI</span>
        <span style={{ flex: 1, height: 1, background: 'var(--rule)' }} />
        <span>An · 2 phút trước</span>
      </div>
      <h1 className="tight" style={{
        fontFamily: 'var(--serif)',
        fontSize: 'clamp(28px, 3.4vw, 42px)',
        lineHeight: 1.1, margin: 0,
        color: 'var(--ink)', letterSpacing: '-0.02em',
        fontWeight: 500,
        textWrap: 'balance',
      }}>
        {q}
      </h1>

      {/* Research narrative */}
      <div style={{
        display: 'flex', flexWrap: 'wrap', gap: 16, marginTop: 18,
        alignItems: 'center',
      }}>
        <ResearchStep label="Quét 2,847 video" done={stage >= 1} active={stage === 0} />
        <ResearchStep label="Phân tích 14 kênh top" done={stage >= 2} active={stage === 1} />
        <ResearchStep label="Tìm pattern chung" done={stage >= 3} active={stage === 2} />
        <ResearchStep label="Viết tóm tắt" done={stage >= 4} active={stage === 3} />
        {done && (
          <span className="chip chip-lime" style={{ marginLeft: 'auto' }}>
            <span className="live-dot" style={{ background: 'var(--ink)' }} />
            HOÀN TẤT · 14 GIÂY
          </span>
        )}
      </div>
    </div>
  );
}

function ResearchStep({ label, done, active }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <span style={{
        width: 14, height: 14, borderRadius: '50%',
        border: '1.5px solid ' + (done ? 'var(--ink)' : 'var(--rule)'),
        background: done ? 'var(--ink)' : active ? 'var(--accent-soft)' : 'transparent',
        color: 'var(--canvas)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 9, fontWeight: 700,
        position: 'relative',
      }}>
        {done ? <Icon name="check" size={8} /> : active ? <span className="pulse-dot" /> : null}
      </span>
      <span className="mono" style={{
        fontSize: 11, color: done ? 'var(--ink)' : active ? 'var(--ink-2)' : 'var(--ink-4)',
        fontWeight: done ? 500 : 400,
      }}>{label}</span>
      <style>{`
        .pulse-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--accent); animation: pulseDot 1s infinite; }
        @keyframes pulseDot { 0%, 100% { opacity: 0.4; transform: scale(0.8); } 50% { opacity: 1; transform: scale(1.1); } }
      `}</style>
    </div>
  );
}

function ProgressPill({ done, stage }) {
  if (done) return (
    <span className="chip mono" style={{ fontSize: 10 }}>
      <Icon name="check" size={10} style={{ color: 'rgb(0, 159, 250)' }} />
      14s · 47 nguồn
    </span>
  );
  return (
    <span className="chip mono" style={{ fontSize: 10, color: 'var(--ink-3)' }}>
      <span className="pulse-dot" style={{ background: 'var(--accent)', width: 6, height: 6, borderRadius: '50%', display: 'inline-block' }} />
      Đang nghiên cứu… {stage + 1}/4
    </span>
  );
}

// ============================================================
// AnswerBlock — editorial section wrapper
// ============================================================

function AnswerBlock({ kicker, title, children, show = true, delay = 0, action }) {
  return (
    <section className={'answer-block ' + (show ? 'show' : '')} style={{
      marginTop: 44, transitionDelay: show ? delay + 'ms' : '0ms',
    }}>
      <div style={{
        display: 'flex', alignItems: 'baseline', justifyContent: 'space-between',
        gap: 12, marginBottom: 14,
      }}>
        <div style={{ minWidth: 0 }}>
          <div className="mono uc" style={{
            fontSize: 10, letterSpacing: '0.18em', color: 'var(--accent)',
            marginBottom: 6, fontWeight: 600,
          }}>{kicker}</div>
          <h2 className="tight" style={{
            fontFamily: 'var(--serif)',
            fontSize: 'clamp(20px, 2.2vw, 26px)',
            lineHeight: 1.15, margin: 0, fontWeight: 500,
            letterSpacing: '-0.01em',
          }}>{title}</h2>
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

function SumStat({ label, value, trend, tone, border }) {
  return (
    <div style={{
      padding: '18px 16px',
      borderLeft: border ? '1px solid var(--ink)' : 'none',
    }}>
      <div className="mono uc" style={{ fontSize: 9, letterSpacing: '0.16em', color: 'var(--ink-4)', marginBottom: 6 }}>{label}</div>
      <div className="tight" style={{
        fontFamily: 'var(--serif)', fontSize: 40, lineHeight: 1, fontWeight: 500, letterSpacing: '-0.02em',
      }}>{value}</div>
      <div className="mono" style={{
        fontSize: 11, marginTop: 6,
        color: tone === 'up' ? 'rgb(0, 159, 250)' : 'var(--ink-3)',
      }}>{tone === 'up' ? '▲ ' : ''}{trend}</div>
    </div>
  );
}

// ============================================================
// Hook finding row
// ============================================================

function HookFinding({ rank, pattern, retention, delta, uses, insight, videos }) {
  return (
    <div style={{
      border: '1px solid var(--rule)',
      borderLeft: '3px solid var(--accent)',
      padding: '18px 20px',
      background: 'var(--paper)',
      display: 'grid',
      gridTemplateColumns: '40px 1fr auto',
      gap: 18,
      alignItems: 'start',
    }}>
      <div className="tight" style={{
        fontFamily: 'var(--serif)', fontSize: 36, lineHeight: 0.9,
        color: 'var(--ink-3)', letterSpacing: '-0.03em', fontWeight: 400,
      }}>{String(rank).padStart(2, '0')}</div>

      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
          <span className="mono" style={{
            background: 'var(--ink)', color: 'var(--canvas)',
            padding: '4px 10px', borderRadius: 4, fontSize: 14,
            fontWeight: 500,
          }}>{pattern}</span>
          <span className="mono" style={{ fontSize: 11, color: 'var(--ink-4)' }}>
            {uses} video · mẫu #{rank}
          </span>
        </div>
        <p style={{ margin: 0, fontSize: 14, lineHeight: 1.55, color: 'var(--ink-2)', maxWidth: 620, textWrap: 'pretty' }}>
          {insight}
          <sup style={{
            marginLeft: 4, fontSize: 10, color: 'var(--accent)',
            fontFamily: 'var(--mono)', fontWeight: 500,
          }}>[{videos.map(v => v + 1).join('][')}]</sup>
        </p>
      </div>

      <div style={{ textAlign: 'right' }}>
        <div className="mono uc" style={{ fontSize: 9, letterSpacing: '0.14em', color: 'var(--ink-4)', marginBottom: 4 }}>RETENTION</div>
        <div className="tight" style={{
          fontFamily: 'var(--serif)', fontSize: 28, lineHeight: 1, fontWeight: 500,
          letterSpacing: '-0.02em',
        }}>{retention}</div>
        <div className="mono" style={{ fontSize: 11, color: 'rgb(0, 159, 250)', marginTop: 4 }}>▲ {delta}</div>
      </div>
    </div>
  );
}

// ============================================================
// Evidence video cards
// ============================================================

const EVIDENCE_VIDEOS = [
  { id: 'e1', creator: '@sammie.tech',  title: 'Mình vừa test ChatGPT Pro và nó...',                  views: '412K', ret: '78%', dur: '0:28', bg: '#1F2A3B', hook: 'Mình vừa test ___ và' },
  { id: 'e2', creator: '@minhtuan.dev', title: 'Mình vừa test con laptop 12tr này và thật sự...',     views: '286K', ret: '74%', dur: '0:34', bg: '#3A2B4A', hook: 'Mình vừa test ___ và' },
  { id: 'e3', creator: '@linhgpt',      title: 'Không ai nói với bạn là Apple Intelligence...',       views: '198K', ret: '69%', dur: '0:31', bg: '#2B3A38', hook: 'Không ai nói với bạn là ___' },
  { id: 'e4', creator: '@huy.codes',    title: 'Không ai nói với bạn là Cursor có chế độ này',        views: '156K', ret: '67%', dur: '0:26', bg: '#433328', hook: 'Không ai nói với bạn là ___' },
  { id: 'e5', creator: '@nganh.tech',   title: 'Lướt thấy iPad Pro M4 mà không thể tin đây là...',     views: '124K', ret: '62%', dur: '0:22', bg: '#382B3D', hook: 'Lướt thấy ___ mà không thể tin' },
  { id: 'e6', creator: '@vietdev',      title: 'Lướt thấy AI này mà không thể tin là free',           views: '98K',  ret: '61%', dur: '0:19', bg: '#2A3544', hook: 'Lướt thấy ___ mà không thể tin' },
];

function EvidenceCard({ video, idx, onOpen }) {
  return (
    <button onClick={onOpen} style={{
      textAlign: 'left', cursor: 'pointer',
      border: '1px solid var(--rule)',
      background: 'var(--paper)', padding: 0, overflow: 'hidden',
      display: 'flex', flexDirection: 'column',
      transition: 'transform 0.15s, box-shadow 0.15s',
    }}
    onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '4px 4px 0 var(--ink)'; }}
    onMouseLeave={e => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.boxShadow = 'none'; }}
    >
      <div style={{
        aspectRatio: '9/12',
        background: `linear-gradient(160deg, ${video.bg}, ${video.bg}dd 60%, #000)`,
        position: 'relative',
        display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
        padding: 10, color: 'white',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <span className="mono" style={{
            background: 'var(--accent)', color: 'white',
            padding: '2px 7px', borderRadius: 3, fontSize: 10, fontWeight: 600,
          }}>[{idx}]</span>
          <span className="mono" style={{
            background: 'rgba(0,0,0,0.6)', padding: '2px 6px', borderRadius: 3, fontSize: 10,
          }}>{video.dur}</span>
        </div>
        <div>
          <div style={{ fontSize: 11, opacity: 0.7, marginBottom: 4 }} className="mono">{video.creator}</div>
          <div style={{ fontSize: 13, lineHeight: 1.3, fontWeight: 500, textWrap: 'pretty' }}>
            {video.title}
          </div>
        </div>
      </div>
      <div style={{
        display: 'flex', justifyContent: 'space-between', padding: '10px 12px',
        borderTop: '1px solid var(--rule)',
        fontSize: 11,
      }}>
        <span className="mono">{video.views}</span>
        <span className="mono" style={{ color: 'rgb(0, 159, 250)' }}>retention {video.ret}</span>
      </div>
    </button>
  );
}

// ============================================================
// Pattern findings — 2x2 grid w/ mini charts
// ============================================================

function PatternCell({ title, finding, detail, chart, leftBorder, topBorder }) {
  return (
    <div style={{
      padding: '20px 22px',
      background: 'var(--paper)',
      borderLeft: leftBorder ? '1px solid var(--ink)' : 'none',
      borderTop: topBorder ? '1px solid var(--ink)' : 'none',
      display: 'flex', flexDirection: 'column', gap: 14,
    }}>
      <div>
        <div className="mono uc" style={{ fontSize: 10, letterSpacing: '0.14em', color: 'var(--ink-4)', marginBottom: 6 }}>{title}</div>
        <div className="tight" style={{
          fontFamily: 'var(--serif)', fontSize: 28, lineHeight: 1.05, fontWeight: 500,
          letterSpacing: '-0.02em',
        }}>{finding}</div>
      </div>
      <div style={{ minHeight: 60 }}>{chart}</div>
      <div style={{ fontSize: 13, lineHeight: 1.5, color: 'var(--ink-3)', textWrap: 'pretty' }}>{detail}</div>
    </div>
  );
}

function DurationChart() {
  const bars = [4, 8, 14, 22, 34, 38, 28, 18, 10, 6, 3, 2];
  const max = Math.max(...bars);
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 3, height: 52 }}>
      {bars.map((b, i) => {
        const inRange = i >= 4 && i <= 7;
        return (
          <div key={i} style={{
            flex: 1, height: (b / max * 100) + '%',
            background: inRange ? 'var(--accent)' : 'var(--ink-5, #D8D4CB)',
            minHeight: 2,
          }} />
        );
      })}
    </div>
  );
}

function HookTimingChart() {
  return (
    <svg viewBox="0 0 200 52" style={{ width: '100%', height: 52 }}>
      <path d="M0 10 Q40 8, 60 14 T120 40 T200 48" fill="none" stroke="var(--ink-4)" strokeWidth="1.5" />
      <rect x="14" y="4" width="24" height="44" fill="var(--accent-soft)" />
      <text x="26" y="18" textAnchor="middle" fontSize="8" fill="var(--accent)" fontFamily="var(--mono)" fontWeight="600">SWEET</text>
      <text x="26" y="28" textAnchor="middle" fontSize="8" fill="var(--accent)" fontFamily="var(--mono)" fontWeight="600">SPOT</text>
      <circle cx="26" cy="42" r="3" fill="var(--accent)" />
    </svg>
  );
}

function SoundMix() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 0, height: 32 }}>
      <div style={{ flex: 62, background: 'var(--accent)', height: '100%', display: 'flex', alignItems: 'center', padding: '0 10px', color: 'white', fontSize: 11, fontWeight: 600 }} className="mono">62% GỐC</div>
      <div style={{ flex: 28, background: 'var(--ink)', height: '100%', display: 'flex', alignItems: 'center', padding: '0 8px', color: 'var(--canvas)', fontSize: 11 }} className="mono">28% TREND</div>
      <div style={{ flex: 10, background: 'var(--ink-5, #D8D4CB)', height: '100%' }} />
    </div>
  );
}

function CtaBars() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span className="mono" style={{ fontSize: 10, width: 60, color: 'var(--ink-3)' }}>HỎI NGƯỢC</span>
        <div style={{ flex: 1, height: 10, background: 'var(--accent)' }} />
        <span className="mono" style={{ fontSize: 10, width: 30, textAlign: 'right' }}>3.4×</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span className="mono" style={{ fontSize: 10, width: 60, color: 'var(--ink-3)' }}>"FOLLOW"</span>
        <div style={{ flex: 1, height: 10, background: 'var(--ink-5, #D8D4CB)' }}>
          <div style={{ width: '29%', height: '100%', background: 'var(--ink-4)' }} />
        </div>
        <span className="mono" style={{ fontSize: 10, width: 30, textAlign: 'right' }}>1.0×</span>
      </div>
    </div>
  );
}

// ============================================================
// Action cards
// ============================================================

function ActionCard({ icon, title, sub, cta, onClick, primary }) {
  return (
    <button onClick={onClick} style={{
      textAlign: 'left', cursor: 'pointer',
      background: primary ? 'var(--ink)' : 'var(--paper)',
      color: primary ? 'var(--canvas)' : 'var(--ink)',
      border: '1px solid var(--ink)',
      padding: '20px 20px 16px',
      display: 'flex', flexDirection: 'column', gap: 10,
      minHeight: 160,
      transition: 'transform 0.15s, box-shadow 0.15s',
    }}
    onMouseEnter={e => { e.currentTarget.style.transform = 'translate(-2px, -2px)'; e.currentTarget.style.boxShadow = (primary ? '4px 4px 0 var(--accent)' : '4px 4px 0 var(--ink)'); }}
    onMouseLeave={e => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.boxShadow = 'none'; }}
    >
      <div style={{
        width: 32, height: 32, borderRadius: 6,
        background: primary ? 'var(--accent)' : 'var(--accent-soft)',
        color: primary ? 'white' : 'var(--accent)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <Icon name={icon} size={16} />
      </div>
      <div style={{
        fontFamily: 'var(--serif)', fontSize: 20, lineHeight: 1.2, fontWeight: 500, letterSpacing: '-0.01em',
      }}>{title}</div>
      <div style={{ fontSize: 13, lineHeight: 1.45, opacity: 0.7, flex: 1, textWrap: 'pretty' }}>{sub}</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 500 }} className="mono">
        {cta} <Icon name="arrow-right" size={11} />
      </div>
    </button>
  );
}

// ============================================================
// Follow-up composer
// ============================================================

function FollowUpComposer({ setRoute, onSubmit }) {
  const [v, setV] = React.useState('');
  const followUps = [
    'Thời điểm đăng nào tốt nhất cho các hook này?',
    'Creator nào dùng pattern này thành công nhất?',
    'Viết kịch bản 30s với hook #1',
  ];
  const submit = () => {
    const q = v.trim();
    if (!q) return;
    onSubmit && onSubmit(q);
    setV('');
  };
  return (
    <section className="answer-block show" style={{ marginTop: 48 }}>
      <div className="mono uc" style={{ fontSize: 10, letterSpacing: '0.18em', color: 'var(--ink-4)', marginBottom: 12 }}>
        TIẾP TỤC NGHIÊN CỨU
      </div>
      <div style={{
        background: 'var(--paper)',
        border: '2px solid var(--ink)',
        borderRadius: 16,
        boxShadow: '4px 4px 0 var(--ink)',
        padding: 4,
      }}>
        <div style={{ padding: '14px 18px 6px' }}>
          <textarea
            value={v}
            onChange={e => setV(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); } }}
            placeholder="Hỏi thêm về kết quả này…"
            rows={2}
            style={{
              width: '100%', border: 0, outline: 0, resize: 'none',
              background: 'transparent', fontFamily: 'var(--sans)',
              fontSize: 15, lineHeight: 1.45, color: 'var(--ink)',
            }}
          />
        </div>
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '8px 10px',
          borderTop: '1px solid var(--rule)',
        }}>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {followUps.map(f => (
              <button key={f} className="chip" onClick={() => { setV(f); setTimeout(() => { onSubmit && onSubmit(f); setV(''); }, 100); }} style={{ cursor: 'pointer', fontSize: 11 }}>
                <Icon name="sparkle" size={10} style={{ color: 'var(--accent)' }} /> {f}
              </button>
            ))}
          </div>
          <button className="btn btn-accent" onClick={submit} disabled={!v.trim()} style={{ opacity: v.trim() ? 1 : 0.4, cursor: v.trim() ? 'pointer' : 'not-allowed' }}>
            Gửi <Icon name="arrow-up" size={11} />
          </button>
        </div>
      </div>
    </section>
  );
}

// ============================================================
// Right rail — sources, related Qs, save
// ============================================================

function Sources({ stage }) {
  return (
    <div style={{
      border: '1px solid var(--rule)', background: 'var(--paper)',
      padding: '18px 18px 14px',
    }}>
      <div className="mono uc" style={{
        fontSize: 10, letterSpacing: '0.18em', color: 'var(--ink-4)',
        marginBottom: 12, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <span>NGUỒN</span>
        <span style={{ color: 'var(--accent)' }}>{stage >= 1 ? '47' : '…'}</span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <SourceRow icon="film"  label="Video TikTok"      count="47" sub="7 ngày gần nhất" />
        <SourceRow icon="eye"   label="Kênh đã quét"      count="14" sub="Top 5% ngách Tech" />
        <SourceRow icon="users" label="Creator đã profile" count="8"  sub="> 100K follower" />
        <SourceRow icon="trend" label="Data điểm"         count="2.4K" sub="Views · retention · CTR" />
      </div>
      <button className="chip" style={{ width: '100%', justifyContent: 'center', marginTop: 14, cursor: 'pointer' }}>
        Xem chi tiết nguồn <Icon name="arrow-right" size={10} />
      </button>
    </div>
  );
}

function SourceRow({ icon, label, count, sub }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <div style={{
        width: 28, height: 28, borderRadius: 4,
        background: 'var(--canvas-2)', border: '1px solid var(--rule)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: 'var(--ink-3)',
      }}>
        <Icon name={icon} size={12} />
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 500, lineHeight: 1.2 }}>{label}</div>
        <div className="mono" style={{ fontSize: 10, color: 'var(--ink-4)', marginTop: 2 }}>{sub}</div>
      </div>
      <div className="mono" style={{ fontSize: 14, fontWeight: 500 }}>{count}</div>
    </div>
  );
}

function RelatedQs({ setRoute, onPick }) {
  const qs = [
    'Hook nào ít dùng nhưng retention cao?',
    'Kênh Tech mới nổi 30 ngày qua?',
    'Thời lượng tối ưu theo từng loại hook?',
    'Pattern nào đang hết trend?',
  ];
  return (
    <div style={{
      border: '1px solid var(--rule)', background: 'var(--paper)',
      padding: '18px 18px 6px', marginTop: 18,
    }}>
      <div className="mono uc" style={{
        fontSize: 10, letterSpacing: '0.18em', color: 'var(--ink-4)', marginBottom: 12,
      }}>CÂU HỎI LIÊN QUAN</div>
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        {qs.map((q, i) => (
          <button key={q} className="related-q" onClick={() => onPick && onPick(q)} style={{
            textAlign: 'left', cursor: 'pointer', background: 'transparent',
            border: 0, borderTop: i > 0 ? '1px solid var(--rule)' : 'none',
            padding: '12px 0', display: 'flex', alignItems: 'center', gap: 10,
            fontSize: 13, lineHeight: 1.4, color: 'var(--ink-2)',
          }}>
            <span style={{ flex: 1, textWrap: 'pretty' }}>{q}</span>
            <Icon name="arrow-right" size={11} style={{ color: 'var(--ink-4)' }} />
          </button>
        ))}
      </div>
      <style>{`
        .related-q:hover { color: var(--accent) !important; }
      `}</style>
    </div>
  );
}

function SaveCard() {
  return (
    <div style={{
      border: '1px solid var(--ink)', background: 'var(--ink)', color: 'var(--canvas)',
      padding: '18px 18px', marginTop: 18,
      display: 'flex', flexDirection: 'column', gap: 12,
    }}>
      <div className="mono uc" style={{ fontSize: 10, letterSpacing: '0.18em', opacity: 0.6 }}>LƯU NGHIÊN CỨU</div>
      <div style={{ fontFamily: 'var(--serif)', fontSize: 18, lineHeight: 1.25, fontWeight: 500, letterSpacing: '-0.01em' }}>
        Biến báo cáo này thành template cho các tuần sau.
      </div>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button className="chip" style={{ background: 'var(--canvas)', color: 'var(--ink)', cursor: 'pointer' }}>
          <Icon name="bookmark" size={11} /> Lưu
        </button>
        <button className="chip" style={{ background: 'transparent', color: 'var(--canvas)', border: '1px solid rgba(255,255,255,0.3)', cursor: 'pointer' }}>
          <Icon name="share" size={11} /> Chia sẻ
        </button>
        <button className="chip" style={{ background: 'transparent', color: 'var(--canvas)', border: '1px solid rgba(255,255,255,0.3)', cursor: 'pointer' }}>
          <Icon name="download" size={11} /> PDF
        </button>
      </div>
    </div>
  );
}

window.AnswerScreen = AnswerScreen;
Object.assign(window, { AnswerBlock, EvidenceCard, ActionCard, ResearchStep, EVIDENCE_VIDEOS });