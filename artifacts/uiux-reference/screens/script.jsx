// ============================================================
// ScriptScreen — Kịch Bản / Xưởng Viết
// Now with structural intelligence woven into the writing tool:
//  - Per-scene corpus overlay (duration, text-overlay style, pacing norm)
//  - Hook-timing meter (live, flags > 1.4s)
//  - Pacing ribbon (scene-length vs niche winners)
//  - Text-overlay library (drop-in from top videos)
//  - Reference clips rail (similar-purpose scenes)
//  - Micro-citations ("Dựa trên 47 video")
// ============================================================

function ScriptScreen({ setRoute }) {
  const [topic, setTopic] = React.useState('Review tai nghe 200k vs 2 triệu');
  const [hookStyle, setHookStyle] = React.useState('Mình vừa test ___ và');
  const [duration, setDuration] = React.useState(32);
  const [activeShot, setActiveShot] = React.useState(0);
  const [hookDelayMs, setHookDelayMs] = React.useState(1200); // user-editable hook landing time

  // Scenes with structural intelligence annotations
  const shots = [
    { t0: 0,  t1: 3,  cam: 'Cận mặt',          voice: 'Mình vừa test tai 2 triệu và thật sự…', viz: 'Tay cầm 2 tai nghe, chữ "200K vs 2TR" to', overlay: 'BOLD CENTER', tip: 'Hook lành trong 1.2s — ok. Không quá dài.', corpusAvg: 2.8, winnerAvg: 2.4, overlayWinner: 'white sans 28pt · bottom-center' },
    { t0: 3,  t1: 8,  cam: 'Cắt nhanh b-roll', voice: 'Khác biệt đầu tiên bạn nghe thấy ngay',  viz: 'Slow-mo unbox, đặt cạnh nhau',                overlay: 'SUB-CAPTION', tip: 'Ngách Tech: scene #2 nên có motion cut ≤ 0.4s', corpusAvg: 4.2, winnerAvg: 5.0, overlayWinner: 'yellow outlined · mid-left' },
    { t0: 8,  t1: 16, cam: 'Side-by-side',     voice: 'Bass 200k bị bí. 2 triệu mở ra như sân khấu.', viz: 'Split-screen visualizer waveform',           overlay: 'STAT BURST', tip: 'Split-screen cần hold ≥ 6s để người xem hiểu', corpusAvg: 7.8, winnerAvg: 8.0, overlayWinner: 'number callout 72pt' },
    { t0: 16, t1: 24, cam: 'POV nghe',         voice: 'Mid-range khác hẳn — đây là test 3 thể loại', viz: 'POV, đèn ấm, tai lớn',                       overlay: 'LABEL', tip: 'POV 8s là giới hạn — cắt trước khi mất attention', corpusAvg: 6.2, winnerAvg: 7.5, overlayWinner: 'caption strip · bottom' },
    { t0: 24, t1: 30, cam: 'Cận tay + texture', voice: 'Build cũng khác. Cảm giác cầm là khác hệ.', viz: 'Xoay tai, ánh sáng bên',                     overlay: 'NONE', tip: 'Scene không text — để visual nói. Thuận ngách.', corpusAvg: 5.1, winnerAvg: 5.0, overlayWinner: '—' },
    { t0: 30, t1: 32, cam: 'Cận mặt + câu hỏi', voice: 'Bạn chọn cái nào? Comment cho mình biết.',  viz: 'Câu hỏi to trên màn',                        overlay: 'QUESTION XL', tip: 'CTA câu hỏi ăn 3.4× "follow để xem thêm"', corpusAvg: 2.4, winnerAvg: 2.5, overlayWinner: 'question mark · full bleed' },
  ];

  return (
    <div style={{ background: 'var(--canvas)', minHeight: '100%' }}>
      <div style={{ maxWidth: 1380, margin: '0 auto', padding: '24px 28px 80px' }}>
        {/* Header */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          marginBottom: 20, paddingBottom: 16, borderBottom: '2px solid var(--ink)',
          gap: 16, flexWrap: 'wrap',
        }}>
          <div style={{ minWidth: 0, flex: 1 }}>
            <div className="mono uc" style={{ fontSize: 10, letterSpacing: '0.18em', color: 'var(--accent)', marginBottom: 6, fontWeight: 600 }}>
              XƯỞNG VIẾT · KỊCH BẢN SỐ 14
            </div>
            <h1 className="tight" style={{
              fontFamily: 'var(--serif)', margin: 0, fontSize: 'clamp(26px, 3vw, 36px)',
              lineHeight: 1.1, fontWeight: 500, letterSpacing: '-0.02em',
            }}>
              {topic}
            </h1>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-ghost"><Icon name="copy" size={12} /> Copy</button>
            <button className="btn btn-ghost"><Icon name="download" size={12} /> PDF</button>
            <button className="btn"><Icon name="film" size={12} /> Chế độ quay</button>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr 300px', gap: 24 }} className="script-layout-3col">
          {/* LEFT — inputs */}
          <aside style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <CardInput label="CHỦ ĐỀ">
              <textarea value={topic} onChange={e => setTopic(e.target.value)} rows={2} style={{
                width: '100%', border: 0, outline: 0, resize: 'none', background: 'transparent',
                fontSize: 16, color: 'var(--ink)', lineHeight: 1.3, fontFamily: 'var(--serif)',
              }} />
            </CardInput>

            <CardInput label="MẪU HOOK · XẾP THEO RETENTION">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {HOOKS.slice(0, 4).map(h => (
                  <button key={h.pattern} onClick={() => setHookStyle(h.pattern)} style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '8px 10px', borderRadius: 4, cursor: 'pointer',
                    background: hookStyle === h.pattern ? 'var(--ink)' : 'var(--canvas-2)',
                    color: hookStyle === h.pattern ? 'var(--canvas)' : 'var(--ink-2)',
                    border: '1px solid ' + (hookStyle === h.pattern ? 'var(--ink)' : 'var(--rule)'),
                    fontSize: 12, textAlign: 'left',
                  }}>
                    <span className="tight" style={{ fontSize: 13 }}>"{h.pattern}"</span>
                    <span className="mono" style={{ fontSize: 10, color: 'rgb(0, 159, 250)' }}>▲{h.delta}</span>
                  </button>
                ))}
              </div>
            </CardInput>

            <CardInput label={<>HOOK RƠI LÚC <span className="mono" style={{ color: hookDelayMs > 1400 ? 'var(--accent)' : 'rgb(0, 159, 250)' }}>{(hookDelayMs/1000).toFixed(1)}s</span></>}>
              <input type="range" min="400" max="3000" step="100" value={hookDelayMs} onChange={e => setHookDelayMs(+e.target.value)} style={{ width: '100%', accentColor: 'var(--accent)' }} />
              <HookTimingMeter delay={hookDelayMs} />
              <div style={{ fontSize: 11, color: 'var(--ink-4)', marginTop: 8, lineHeight: 1.45 }}>
                Video thắng trong ngách Tech rơi hook tại <span className="mono" style={{ color: 'var(--ink-2)' }}>0.8–1.4s</span>. Sau 1.4s, retention giảm <span className="mono" style={{ color: 'var(--accent)' }}>38%</span>.
              </div>
            </CardInput>

            <CardInput label={<>ĐỘ DÀI · <span className="mono">{duration}s</span></>}>
              <input type="range" min="15" max="90" value={duration} onChange={e => setDuration(+e.target.value)} style={{ width: '100%', accentColor: 'var(--accent)' }} />
              <DurationInsight duration={duration} />
            </CardInput>

            <CardInput label="GIỌNG ĐIỆU">
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {['Hài', 'Chuyên gia', 'Tâm sự', 'Năng lượng', 'Mỉa mai'].map((t, i) => (
                  <span key={t} className={i === 1 ? 'chip chip-accent' : 'chip'} style={{ cursor: 'pointer' }}>{t}</span>
                ))}
              </div>
            </CardInput>

            <button className="btn btn-accent" style={{ justifyContent: 'center' }}>
              <Icon name="sparkle" size={13} /> Tạo lại với AI
            </button>

            <CitationTag n={47} />
          </aside>

          {/* MIDDLE — storyboard + pacing ribbon */}
          <div>
            <PacingRibbon shots={shots} duration={duration} activeShot={activeShot} setActiveShot={setActiveShot} />

            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 14 }}>
              {shots.map((s, i) => (
                <ShotRow
                  key={i} shot={s} idx={i}
                  active={activeShot === i}
                  onClick={() => setActiveShot(i)}
                />
              ))}
            </div>

            <ForecastBar duration={duration} hookDelay={hookDelayMs} />
          </div>

          {/* RIGHT — structural intelligence for active scene */}
          <aside className="script-right" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <SceneIntelligence shot={shots[activeShot]} idx={activeShot} setRoute={setRoute} />
          </aside>
        </div>
      </div>

      <style>{`
        @media (max-width: 1240px) {
          .script-layout-3col { grid-template-columns: 280px 1fr !important; }
          .script-right { grid-column: 1 / -1; flex-direction: row !important; overflow-x: auto; }
          .script-right > * { min-width: 280px; flex: 1; }
        }
        @media (max-width: 880px) {
          .script-layout-3col { grid-template-columns: 1fr !important; }
          .script-right { flex-direction: column !important; }
          .script-right > * { min-width: 0; }
        }
      `}</style>
    </div>
  );
}

// ----- Small input card wrapper -----
function CardInput({ label, children }) {
  return (
    <div style={{
      border: '1px solid var(--rule)', background: 'var(--paper)',
      padding: 14,
    }}>
      <div className="mono uc" style={{ fontSize: 9.5, letterSpacing: '0.16em', color: 'var(--ink-4)', marginBottom: 10, fontWeight: 500 }}>{label}</div>
      {children}
    </div>
  );
}

// ----- Hook timing meter (visual band) -----
function HookTimingMeter({ delay }) {
  const pct = Math.min(100, (delay / 3000) * 100);
  const inSweet = delay >= 800 && delay <= 1400;
  return (
    <div style={{ position: 'relative', height: 14, marginTop: 8 }}>
      <div style={{ position: 'absolute', inset: 0, background: 'var(--canvas-2)' }} />
      <div style={{ position: 'absolute', left: (800/3000*100) + '%', right: (100 - 1400/3000*100) + '%', top: 0, bottom: 0, background: 'rgba(0, 159, 250, 0.22)', borderLeft: '1px dashed rgb(0, 159, 250)', borderRight: '1px dashed rgb(0, 159, 250)' }} />
      <div style={{ position: 'absolute', left: `calc(${pct}% - 1.5px)`, top: -4, bottom: -4, width: 3, background: inSweet ? 'rgb(0, 159, 250)' : 'var(--accent)' }} />
      <div style={{ position: 'absolute', top: 18, left: 0, right: 0, display: 'flex', justifyContent: 'space-between', fontSize: 9, color: 'var(--ink-4)' }} className="mono">
        <span>0s</span><span>1s</span><span>2s</span><span>3s</span>
      </div>
    </div>
  );
}

// ----- Duration insight -----
function DurationInsight({ duration }) {
  let msg, tone;
  if (duration < 22)      { msg = 'Ngắn — phù hợp hook thuần, ít dữ liệu'; tone = 'var(--ink-4)'; }
  else if (duration <= 40){ msg = '★ Vùng vàng — 71% video thắng nằm đây'; tone = 'rgb(0, 159, 250)'; }
  else if (duration <= 60){ msg = 'Dài hơn TB — cần payoff rõ lúc 40s'; tone = 'var(--ink-4)'; }
  else                    { msg = '⚠ > 60s retention giảm 34%'; tone = 'var(--accent)'; }
  return <div style={{ fontSize: 11, color: tone, marginTop: 8, lineHeight: 1.45 }} className="mono">{msg}</div>;
}

// ----- Pacing ribbon — visual tempo across shots -----
function PacingRibbon({ shots, duration, activeShot, setActiveShot }) {
  const total = shots[shots.length - 1].t1;
  return (
    <div style={{
      border: '1px solid var(--ink)', background: 'var(--paper)',
      padding: 14,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
        <div>
          <div className="mono uc" style={{ fontSize: 10, letterSpacing: '0.16em', color: 'var(--ink-4)', marginBottom: 4 }}>NHỊP ĐỘ · PACING RIBBON</div>
          <div style={{ fontSize: 13, color: 'var(--ink-2)' }}>
            Tempo kịch bản vs <span style={{ color: 'rgb(0, 159, 250)' }}>video thắng trong ngách</span>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <LegendDot c="var(--accent)" label="Của bạn" />
          <LegendDot c="rgb(0, 159, 250)" label="Ngách" />
        </div>
      </div>

      {/* Shot bars */}
      <div style={{ display: 'flex', gap: 2, height: 38 }}>
        {shots.map((s, i) => {
          const w = ((s.t1 - s.t0) / total) * 100;
          const yoursH = Math.min(100, ((s.t1 - s.t0) / (s.winnerAvg * 2)) * 60 + 30);
          const nicheH = Math.min(100, (s.winnerAvg / (s.winnerAvg * 2)) * 60 + 30);
          const slow = (s.t1 - s.t0) > s.winnerAvg * 1.2;
          return (
            <button key={i} onClick={() => setActiveShot(i)} style={{
              flex: w, position: 'relative', cursor: 'pointer',
              border: 0, padding: 0,
              background: activeShot === i ? 'var(--accent-soft)' : 'transparent',
              transition: 'background 0.15s',
            }} title={`Shot 0${i+1}`}>
              <div style={{ position: 'absolute', left: '20%', width: '25%', bottom: 0, height: yoursH + '%', background: slow ? 'var(--accent)' : 'var(--ink)' }} />
              <div style={{ position: 'absolute', left: '55%', width: '25%', bottom: 0, height: nicheH + '%', background: 'rgb(0, 159, 250)', opacity: 0.5 }} />
              <div style={{ position: 'absolute', top: 0, left: 3, fontSize: 9, color: 'var(--ink-4)' }} className="mono">0{i+1}</div>
            </button>
          );
        })}
      </div>

      {/* Timeline */}
      <div style={{ display: 'flex', marginTop: 4, position: 'relative', height: 16 }}>
        {shots.map((s, i) => (
          <div key={i} style={{
            flex: (s.t1 - s.t0) / total,
            borderLeft: i > 0 ? '1px solid var(--rule)' : 'none',
            paddingLeft: 3, paddingTop: 2,
            fontSize: 9, color: 'var(--ink-4)',
          }} className="mono">{s.t0}s</div>
        ))}
      </div>
    </div>
  );
}

function LegendDot({ c, label }) {
  return <span className="mono" style={{ fontSize: 10, color: 'var(--ink-3)', display: 'inline-flex', alignItems: 'center', gap: 5 }}><span style={{ width: 8, height: 8, background: c, display: 'inline-block' }} />{label}</span>;
}

// ----- Shot row -----
function ShotRow({ shot, idx, active, onClick }) {
  const slow = (shot.t1 - shot.t0) > shot.winnerAvg * 1.2;
  return (
    <div onClick={onClick} style={{
      display: 'grid', gridTemplateColumns: '90px 100px 1fr 1fr',
      border: '1px solid ' + (active ? 'var(--ink)' : 'var(--rule)'),
      background: 'var(--paper)', overflow: 'hidden', cursor: 'pointer',
      boxShadow: active ? '3px 3px 0 var(--ink)' : 'none',
      transition: 'box-shadow 0.12s, border-color 0.12s',
    }}>
      <div style={{
        padding: 12, background: active ? 'var(--ink)' : idx === 0 ? 'var(--accent)' : 'var(--canvas-2)',
        color: active ? 'var(--canvas)' : idx === 0 ? 'white' : 'var(--ink-2)',
      }}>
        <div className="mono" style={{ fontSize: 10, opacity: 0.7, marginBottom: 4 }}>SHOT 0{idx+1}</div>
        <div className="mono" style={{ fontSize: 12, fontWeight: 600 }}>{shot.t0}–{shot.t1}s</div>
        <div className="mono" style={{ fontSize: 9, opacity: 0.7, marginTop: 4 }}>{shot.t1 - shot.t0}s</div>
      </div>
      <div style={{
        background: ['#3A4A5C', '#2A3A5C', '#3D2F4A', '#4A2A3D', '#2A4A5C', '#5C2A3A'][idx % 6],
        position: 'relative', display: 'flex', alignItems: 'flex-end', padding: 8,
      }}>
        <span style={{ color: 'rgba(255,255,255,0.85)', fontSize: 11 }} className="mono">{shot.cam}</span>
      </div>
      <div style={{ padding: 12, borderRight: '1px solid var(--rule)' }}>
        <div className="mono uc" style={{ fontSize: 9, color: 'var(--ink-4)', marginBottom: 4 }}>LỜI THOẠI</div>
        <div className="tight" style={{ fontSize: 13.5, lineHeight: 1.35, color: 'var(--ink)', fontFamily: 'var(--serif)' }}>"{shot.voice}"</div>
      </div>
      <div style={{ padding: 12, position: 'relative' }}>
        <div className="mono uc" style={{ fontSize: 9, color: 'var(--ink-4)', marginBottom: 4 }}>HÌNH ẢNH · {shot.overlay}</div>
        <div style={{ fontSize: 12, color: 'var(--ink-3)', marginBottom: 8, lineHeight: 1.4 }}>{shot.viz}</div>
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 5,
          background: slow ? 'var(--accent-soft)' : 'rgba(0, 159, 250, 0.12)',
          color: slow ? 'var(--accent-deep)' : 'rgb(0, 159, 250)',
          padding: '2px 7px', borderRadius: 3,
          fontSize: 10, fontWeight: 500,
        }} className="mono">
          {slow ? '⚠' : '✓'} {(shot.t1 - shot.t0).toFixed(1)}s · ngách {shot.winnerAvg}s
        </div>
      </div>
    </div>
  );
}

// ----- Scene intelligence (right rail) -----
function SceneIntelligence({ shot, idx, setRoute }) {
  const slow = (shot.t1 - shot.t0) > shot.winnerAvg * 1.2;
  return (
    <>
      <div style={{
        border: '1px solid var(--ink)', background: 'var(--ink)', color: 'var(--canvas)',
        padding: 16,
      }}>
        <div className="mono uc" style={{ fontSize: 10, letterSpacing: '0.16em', opacity: 0.6, marginBottom: 8 }}>
          SHOT 0{idx+1} · PHÂN TÍCH CẤU TRÚC
        </div>
        <div style={{ fontFamily: 'var(--serif)', fontSize: 18, lineHeight: 1.25, fontWeight: 500, letterSpacing: '-0.01em', textWrap: 'pretty' }}>
          {shot.tip}
        </div>
      </div>

      {/* Scene length diagnostic */}
      <div style={{ border: '1px solid var(--rule)', background: 'var(--paper)', padding: 14 }}>
        <div className="mono uc" style={{ fontSize: 9.5, letterSpacing: '0.16em', color: 'var(--ink-4)', marginBottom: 10 }}>ĐỘ DÀI SHOT</div>
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 10 }}>
          <span className="tight" style={{ fontFamily: 'var(--serif)', fontSize: 28, fontWeight: 500, letterSpacing: '-0.02em' }}>
            {(shot.t1 - shot.t0).toFixed(1)}s
          </span>
          <span className="mono" style={{ fontSize: 11, color: slow ? 'var(--accent)' : 'rgb(0, 159, 250)' }}>
            {slow ? `▲ dài hơn ${((shot.t1 - shot.t0) - shot.winnerAvg).toFixed(1)}s` : '✓ đúng nhịp ngách'}
          </span>
        </div>
        <MiniBarCompare yours={shot.t1 - shot.t0} corpus={shot.corpusAvg} winner={shot.winnerAvg} />
        <div style={{ fontSize: 11, color: 'var(--ink-4)', marginTop: 10, lineHeight: 1.5 }}>
          Ngách trung bình <span className="mono" style={{ color: 'var(--ink-2)' }}>{shot.corpusAvg}s</span> ·
          winner <span className="mono" style={{ color: 'rgb(0, 159, 250)' }}>{shot.winnerAvg}s</span>
        </div>
      </div>

      {/* Text overlay library */}
      <div style={{ border: '1px solid var(--rule)', background: 'var(--paper)', padding: 14 }}>
        <div className="mono uc" style={{ fontSize: 9.5, letterSpacing: '0.16em', color: 'var(--ink-4)', marginBottom: 10 }}>TEXT OVERLAY · THƯ VIỆN</div>
        <div style={{ fontSize: 12, color: 'var(--ink-3)', marginBottom: 10, lineHeight: 1.5 }}>
          Trong 47 video thắng, scene loại này dùng:
          <div style={{ fontSize: 13, color: 'var(--ink)', fontWeight: 500, marginTop: 4 }} className="mono">{shot.overlayWinner}</div>
        </div>
        {shot.overlay !== 'NONE' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {OVERLAY_SAMPLES[shot.overlay]?.slice(0, 3).map((o, i) => (
              <button key={i} className="chip" style={{ justifyContent: 'space-between', cursor: 'pointer', padding: '7px 10px', fontSize: 11 }}>
                <span>{o}</span>
                <Icon name="plus" size={10} />
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Reference clips */}
      <div style={{ border: '1px solid var(--rule)', background: 'var(--paper)', padding: 14 }}>
        <div className="mono uc" style={{ fontSize: 9.5, letterSpacing: '0.16em', color: 'var(--ink-4)', marginBottom: 10 }}>CLIP THAM KHẢO</div>
        <div style={{ display: 'flex', gap: 8, overflowX: 'auto' }}>
          {[0, 1, 2].map(i => (
            <button key={i} onClick={() => setRoute('video')} style={{
              flexShrink: 0, width: 80, aspectRatio: '9/13',
              background: ['#2B3A5C', '#3D2B4A', '#4A2B2B'][i],
              border: 0, padding: 0, position: 'relative', cursor: 'pointer',
              color: 'white', display: 'flex', flexDirection: 'column', justifyContent: 'flex-end',
              paddingBlock: 6, paddingInline: 5,
            }}>
              <div className="mono" style={{ fontSize: 9, opacity: 0.7 }}>{['@sammie', '@minhtuan', '@linhgpt'][i]}</div>
              <div style={{ fontSize: 10, lineHeight: 1.2, textAlign: 'left', textWrap: 'pretty' }}>{['Scene POV', 'Split-A/B', 'Hook cận'][i]}</div>
              <div style={{ position: 'absolute', top: 4, right: 4, background: 'rgba(0,0,0,0.6)', padding: '1px 4px', fontSize: 9 }} className="mono">{['5.2s', '7.8s', '2.4s'][i]}</div>
            </button>
          ))}
        </div>
        <div style={{ fontSize: 11, color: 'var(--ink-4)', marginTop: 10, lineHeight: 1.45 }}>
          3 scene cùng mục đích từ video thắng tuần này.
        </div>
      </div>
    </>
  );
}

const OVERLAY_SAMPLES = {
  'BOLD CENTER': ['200K VS 2TR', 'TEST THẬT', 'BẠN CHỌN?'],
  'SUB-CAPTION': ['"khác biệt ngay đầu tiên"', '"chỉ sau 3 giây"', '"thật sự bất ngờ"'],
  'STAT BURST':  ['+248% BASS', '2.4× THÊM CHI TIẾT', '72% PEOPLE'],
  'LABEL':       ['POV · test 3 thể loại', 'Pop · Vocal · Rock', 'Sample #1'],
  'QUESTION XL': ['BẠN CHỌN GÌ?', '200K HAY 2TR?', 'COMMENT THỬ NÀO'],
};

function MiniBarCompare({ yours, corpus, winner }) {
  const max = Math.max(yours, corpus, winner) * 1.1;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
      <Bar label="Của bạn"    v={yours}  max={max} color="var(--accent)" bold />
      <Bar label="Ngách TB"   v={corpus} max={max} color="var(--ink-3)" />
      <Bar label="Winner"     v={winner} max={max} color="rgb(0, 159, 250)" />
    </div>
  );
}
function Bar({ label, v, max, color, bold }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <span className="mono" style={{ fontSize: 10, width: 64, color: 'var(--ink-4)' }}>{label}</span>
      <div style={{ flex: 1, height: 12, background: 'var(--canvas-2)', position: 'relative' }}>
        <div style={{ width: (v / max * 100) + '%', height: '100%', background: color }} />
      </div>
      <span className="mono" style={{ fontSize: 10, width: 32, textAlign: 'right', color: color, fontWeight: bold ? 600 : 400 }}>{v.toFixed(1)}s</span>
    </div>
  );
}

// ----- Forecast bar -----
function ForecastBar({ duration, hookDelay }) {
  const hookScore = hookDelay <= 1400 ? 8.4 : hookDelay <= 2000 ? 6.2 : 4.1;
  const goodLen = duration >= 22 && duration <= 40;
  return (
    <div style={{
      marginTop: 16, padding: '16px 20px',
      background: 'var(--ink)', color: 'var(--canvas)',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      flexWrap: 'wrap', gap: 12,
    }}>
      <div>
        <div className="mono uc" style={{ fontSize: 9.5, letterSpacing: '0.16em', opacity: 0.5, marginBottom: 4 }}>DỰ KIẾN HIỆU SUẤT</div>
        <div style={{ fontSize: 14 }}>
          <span className="tight" style={{ fontFamily: 'var(--serif)', fontSize: 28, fontWeight: 500 }}>~{goodLen ? 62 : 34}K</span>
          <span style={{ opacity: 0.6 }}> view · </span>
          giữ chân <span style={{ color: 'rgb(0, 159, 250)' }}>{goodLen ? 72 : 54}%</span> · hook <span style={{ color: 'var(--accent)' }}>{hookScore.toFixed(1)}/10</span>
        </div>
      </div>
      <button className="btn btn-accent">Lưu vào lịch quay <Icon name="arrow-right" size={11} /></button>
    </div>
  );
}

function CitationTag({ n }) {
  return (
    <div style={{
      padding: '10px 12px', border: '1px dashed var(--rule)',
      fontSize: 10, color: 'var(--ink-4)', lineHeight: 1.5,
    }} className="mono">
      ✻ Gợi ý dựa trên <span style={{ color: 'var(--ink-2)', fontWeight: 500 }}>{n} video</span> trong ngách Tech · 7 ngày gần nhất
    </div>
  );
}

window.ScriptScreen = ScriptScreen;
