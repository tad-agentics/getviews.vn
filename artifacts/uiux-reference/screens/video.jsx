// ============================================================
// Video deep-dive — analysis result page
// ============================================================

function VideoScreen({ setRoute }) {
  const [mode, setMode] = React.useState('win'); // 'win' | 'flop'
  const v = VIDEOS[10]; // breakout AI tools
  return (
    <div style={{ background: 'var(--canvas)', minHeight: '100%' }}>
      <div style={{ maxWidth: 1280, margin: '0 auto', padding: '24px 28px 80px' }}>
        {/* Mode toggle */}
        <div style={{ display: 'flex', gap: 0, border: '1px solid var(--ink)', width: 'fit-content', marginBottom: 14 }}>
          {[['win', 'Vì sao video NỔ', 'sparkle'], ['flop', 'Vì sao video FLOP', 'flame']].map(([k, lbl, ic]) => (
            <button key={k} onClick={() => setMode(k)} style={{
              padding: '8px 14px', cursor: 'pointer',
              background: mode === k ? 'var(--ink)' : 'transparent',
              color: mode === k ? 'var(--canvas)' : 'var(--ink)',
              border: 0, fontSize: 12, fontWeight: 500,
              display: 'flex', alignItems: 'center', gap: 6,
            }}>
              <Icon name={ic} size={12} /> {lbl}
            </button>
          ))}
        </div>
        {mode === 'flop' && <FlopDiagnostic setRoute={setRoute} />}
        {mode === 'win' && <WinAnalysis v={v} setRoute={setRoute} />}
      </div>
    </div>
  );
}

function WinAnalysis({ v, setRoute }) {
  return (
    <>
        {/* Crumbs + actions */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 18 }}>
          <button onClick={() => setRoute('trends')} className="btn btn-ghost"><Icon name="arrow-left" size={12} /> Quay lại Xu Hướng</button>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-ghost"><Icon name="bookmark" size={12} /> Lưu</button>
            <button className="btn btn-ghost"><Icon name="copy" size={12} /> Copy hook</button>
            <button className="btn"><Icon name="script" size={12} /> Tạo kịch bản từ video này</button>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: 32 }} className="video-layout">
          {/* Left — phone preview */}
          <div>
            <div style={{
              aspectRatio: '9/16', borderRadius: 18, background: v.bg,
              position: 'relative', overflow: 'hidden',
              border: '8px solid var(--ink)', boxShadow: '0 30px 60px -30px rgba(0,0,0,0.4)',
            }}>
              <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(180deg, transparent 50%, rgba(0,0,0,0.6))' }} />
              <div style={{ position: 'absolute', top: 12, left: 12, display: 'flex', gap: 4 }}>
                <span style={{ background: 'var(--accent)', color: 'white', padding: '3px 7px', borderRadius: 3, fontSize: 10, fontWeight: 700, letterSpacing: '0.05em' }}>BREAKOUT</span>
              </div>
              <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white' }}>
                <div style={{ width: 56, height: 56, borderRadius: '50%', background: 'rgba(255,255,255,0.2)', backdropFilter: 'blur(10px)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Icon name="play" size={20} />
                </div>
              </div>
              <div style={{ position: 'absolute', bottom: 16, left: 14, right: 14, color: 'white' }}>
                <div className="mono" style={{ fontSize: 11, opacity: 0.8 }}>{v.creator} · {v.dur}</div>
                <div className="tight" style={{ fontSize: 18, lineHeight: 1.15, marginTop: 4 }}>{v.title}</div>
              </div>
            </div>
            <div style={{ marginTop: 12, fontSize: 11, color: 'var(--ink-4)', textAlign: 'center' }} className="mono uc">
              Đăng 18.04 · 234K view · 6.8K save · 4.2K share
            </div>
          </div>

          {/* Right — analysis */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>
            <div>
              <div className="mono uc" style={{ fontSize: 9.5, color: 'var(--ink-4)' }}>BÁO CÁO PHÂN TÍCH · TECH</div>
              <h1 className="tight" style={{ margin: '6px 0 8px', fontSize: 42, lineHeight: 1.05 }}>
                Tại sao "5 app AI mà chưa ai nói" lại nổ?
              </h1>
              <div style={{ fontSize: 15, color: 'var(--ink-3)', maxWidth: 640 }}>
                Video chạm 234K view trong 18 giờ — nhanh gấp 12× trung bình kênh. Đây là 4 yếu tố chính kích lan toả.
              </div>
            </div>

            {/* Big numbers */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 0, border: '1px solid var(--rule)', borderRadius: 10, overflow: 'hidden' }}>
              {[
                { label: 'VIEW', value: '234K', delta: '12× kênh' },
                { label: 'GIỮ CHÂN', value: '78%', delta: 'top 5%' },
                { label: 'SAVE RATE', value: '2.9%', delta: 'rất cao' },
                { label: 'SHARE', value: '4.2K', delta: 'lan ra Threads' },
              ].map((m, i) => (
                <div key={m.label} style={{
                  padding: 18, background: 'var(--paper)',
                  borderRight: i < 3 ? '1px solid var(--rule)' : 0,
                }}>
                  <div className="mono uc" style={{ fontSize: 9, color: 'var(--ink-4)', marginBottom: 6 }}>{m.label}</div>
                  <div className="tight" style={{ fontSize: 30, lineHeight: 1 }}>{m.value}</div>
                  <div className="mono" style={{ fontSize: 10, color: 'var(--pos-deep)', marginTop: 6 }}>{m.delta}</div>
                </div>
              ))}
            </div>

            {/* Timeline */}
            <div>
              <SectionMini kicker="DÒNG THỜI GIAN" title="Cấu trúc 58 giây" />
              <Timeline />
            </div>

            {/* Hook breakdown */}
            <div>
              <SectionMini kicker="GIẢI MÃ HOOK" title="3 giây đầu — vì sao bạn không lướt qua?" />
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
                {[
                  { t: '0.0–0.8s', label: 'Visual shock', body: 'Cận mặt + chữ to "5 app AI" — 1.2s đầu chỉ có chữ và nhịp nhạc giật.' },
                  { t: '0.8–1.8s', label: 'Lời hứa', body: '"…mà chưa ai nói" — đặt câu hỏi tò mò, dùng cấu trúc loại trừ.' },
                  { t: '1.8–3.0s', label: 'Cam kết thời lượng', body: '"Trong 60 giây" — đặt expectation rõ ràng, giúp giữ chân.' },
                ].map((h, i) => (
                  <div key={i} className="card" style={{ padding: 16 }}>
                    <div className="mono" style={{ fontSize: 10, color: 'var(--accent-deep)', marginBottom: 6 }}>{h.t}</div>
                    <div className="tight" style={{ fontSize: 16, marginBottom: 6 }}>{h.label}</div>
                    <div style={{ fontSize: 12, color: 'var(--ink-3)' }}>{h.body}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Lessons */}
            <div>
              <SectionMini kicker="BÀI HỌC ÁP DỤNG" title="3 điều bạn có thể copy" />
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {[
                  ['Mở bằng cấu trúc loại trừ', '"X mà chưa ai nói" tạo cảm giác insider — dùng được cho mọi ngách.'],
                  ['Đặt cam kết thời lượng', 'Nói rõ "trong 60s" giúp người xem chấp nhận ở lại đến hết.'],
                  ['Listicle ngắn 5 mục, mỗi mục ≤8s', 'Tốc độ chuyển nhanh → tăng giữ chân, dễ rewatch để bắt sót.'],
                ].map(([t, b], i) => (
                  <div key={i} style={{
                    display: 'grid', gridTemplateColumns: '40px 1fr auto', gap: 16, alignItems: 'center',
                    padding: '14px 18px', background: 'var(--paper)',
                    border: '1px solid var(--rule)', borderRadius: 8,
                  }}>
                    <div className="tight" style={{ fontSize: 24, color: 'var(--accent)' }}>0{i+1}</div>
                    <div>
                      <div className="tight" style={{ fontSize: 17, marginBottom: 2 }}>{t}</div>
                      <div style={{ fontSize: 12, color: 'var(--ink-3)' }}>{b}</div>
                    </div>
                    <button className="chip">Áp dụng</button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

      <style>{`
        @media (max-width: 900px) {
          .video-layout { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </>
  );
}

function FlopDiagnostic({ setRoute }) {
  const [url, setUrl] = React.useState('https://www.tiktok.com/@ban.test/video/7324...');
  const [analyzed, setAnalyzed] = React.useState(true);
  const issues = [
    { sev: 'high', t: 0.0, end: 1.8, title: 'Hook rơi lúc 1.8s — muộn 0.4s',
      detail: 'Scene mở đầu là logo + intro animation dài 1.8s. Người xem trong ngách Tech bỏ qua ở giây 1.5. Pattern thắng: vào thẳng hook trong 1.2s.',
      fix: 'Cắt bỏ intro · mở bằng câu hội thoại "Mình vừa test ___"' },
    { sev: 'high', t: 8, end: 22, title: 'Scene giải thích 14s liên tục không cắt',
      detail: 'Từ giây 8–22, camera giữ nguyên 1 góc, không có motion cut. 68% người xem drop-off trong khoảng này. Ngách Tech: cắt ≤ 4s.',
      fix: 'Chia thành 3 scene · thêm b-roll sản phẩm · overlay text highlight' },
    { sev: 'mid', t: 22, end: 35, title: 'Text overlay quá nhỏ & màu xám',
      detail: 'Font 14pt màu xám trên nền ảnh mờ. 72% người xem không tắt phụ đề — nhưng text của bạn không đọc được. Winners dùng 28pt white/yellow.',
      fix: 'Font 28pt · white với outline đen · bottom-center' },
    { sev: 'mid', t: 40, end: 58, title: 'CTA "follow để xem thêm" — pattern đang hết trend',
      detail: 'CTA dạng imperative giảm 34% engage so với câu hỏi. Pattern thắng: "Bạn thấy sao? Comment cho mình biết".',
      fix: 'Đổi CTA thành câu hỏi mở · bỏ chữ "follow"' },
  ];

  return (
    <>
      {/* Input */}
      <div style={{
        border: '2px solid var(--ink)', background: 'var(--paper)', padding: 16,
        marginBottom: 24, display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap',
      }}>
        <Icon name="film" size={16} />
        <input value={url} onChange={e => setUrl(e.target.value)} style={{
          flex: 1, minWidth: 260, border: 0, outline: 0, background: 'transparent',
          fontSize: 14, fontFamily: 'var(--mono)', color: 'var(--ink)',
        }} />
        <button className="btn btn-accent" onClick={() => setAnalyzed(true)}>
          <Icon name="sparkle" size={12} /> Phân tích
        </button>
      </div>

      {analyzed && (
        <>
          {/* Summary */}
          <div style={{ borderTop: '2px solid var(--ink)', paddingTop: 22, marginBottom: 28 }}>
            <div className="mono uc" style={{ fontSize: 10, letterSpacing: '0.18em', color: 'var(--accent)', marginBottom: 10, fontWeight: 600 }}>
              CHẨN ĐOÁN · 4 ĐIỂM LỖI CẤU TRÚC
            </div>
            <h1 className="tight" style={{
              fontFamily: 'var(--serif)', margin: 0, fontSize: 'clamp(26px, 3vw, 36px)',
              lineHeight: 1.1, fontWeight: 500, letterSpacing: '-0.02em', maxWidth: 820, textWrap: 'pretty',
            }}>
              Video dừng ở <em style={{ color: 'var(--accent)' }}>8.4K view</em> vì hook rơi muộn và scene thứ 2 giữ quá lâu. 2 thay đổi cấu trúc có thể đẩy lên <span style={{ color: 'rgb(0, 159, 250)' }}>~34K</span>.
            </h1>
            <div style={{ display: 'flex', gap: 18, marginTop: 14, flexWrap: 'wrap', fontSize: 12 }} className="mono">
              <span style={{ color: 'var(--ink-3)' }}>8.4K view · 23% retention · 1.2% CTR</span>
              <span style={{ color: 'var(--ink-4)' }}>/</span>
              <span style={{ color: 'var(--ink-3)' }}>Ngách Tech TB: 42K · 58% ret · 3.4% CTR</span>
              <span style={{ color: 'var(--ink-4)' }}>/</span>
              <span style={{ color: 'var(--ink-4)' }}>So sánh với 47 video thắng</span>
            </div>
          </div>

          {/* Retention curve */}
          <div style={{ border: '1px solid var(--rule)', background: 'var(--paper)', padding: 18, marginBottom: 24 }}>
            <div className="mono uc" style={{ fontSize: 10, letterSpacing: '0.16em', color: 'var(--ink-4)', marginBottom: 12 }}>ĐƯỜNG GIỮ CHÂN · VS NGÁCH</div>
            <svg viewBox="0 0 400 80" style={{ width: '100%', height: 80 }}>
              <path d="M0 6 Q60 10, 120 18 T200 38 T280 58 T400 72" fill="none" stroke="var(--accent)" strokeWidth="2.5" />
              <path d="M0 6 Q80 8, 160 14 T280 32 T400 52" fill="none" stroke="rgb(0, 159, 250)" strokeWidth="1.5" strokeDasharray="4 3" />
              <circle cx="12" cy="6" r="3" fill="var(--accent)" />
              <text x="20" y="10" fontSize="9" fontFamily="var(--mono)" fill="var(--accent)">drop -40% @ 1.8s</text>
              <text x="160" y="36" fontSize="9" fontFamily="var(--mono)" fill="var(--accent)">drop -68% @ 8–22s</text>
            </svg>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4, fontSize: 10 }} className="mono">
              {['0s', '15s', '30s', '45s', '58s'].map(t => <span key={t} style={{ color: 'var(--ink-4)' }}>{t}</span>)}
            </div>
          </div>

          {/* Issues list */}
          <div className="mono uc" style={{ fontSize: 10, letterSpacing: '0.16em', color: 'var(--ink-4)', marginBottom: 10 }}>LỖI CẤU TRÚC · XẾP THEO ẢNH HƯỞNG</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 24 }}>
            {issues.map((r, i) => (
              <div key={i} style={{
                display: 'grid', gridTemplateColumns: '80px 1fr auto',
                gap: 16, padding: '14px 16px',
                background: 'var(--paper)',
                border: '1px solid ' + (r.sev === 'high' ? 'var(--accent)' : 'var(--rule)'),
                borderLeft: '4px solid ' + (r.sev === 'high' ? 'var(--accent)' : 'var(--ink-4)'),
              }}>
                <div>
                  <div className="mono" style={{ fontSize: 11, color: 'var(--ink-4)' }}>{r.t}s – {r.end}s</div>
                  <div className="mono uc" style={{ fontSize: 9, letterSpacing: '0.14em', marginTop: 4, color: r.sev === 'high' ? 'var(--accent)' : 'var(--ink-4)' }}>
                    {r.sev === 'high' ? 'CAO' : 'TB'}
                  </div>
                </div>
                <div>
                  <div style={{ fontFamily: 'var(--serif)', fontSize: 18, fontWeight: 500, lineHeight: 1.25, letterSpacing: '-0.01em' }}>{r.title}</div>
                  <div style={{ fontSize: 13, color: 'var(--ink-3)', marginTop: 6, lineHeight: 1.55, textWrap: 'pretty' }}>{r.detail}</div>
                  <div style={{ fontSize: 12, color: 'var(--ink-2)', marginTop: 8, padding: '6px 10px', background: 'var(--canvas-2)', display: 'inline-block' }}>
                    <span className="mono uc" style={{ fontSize: 9, color: 'var(--accent)', letterSpacing: '0.14em', marginRight: 6 }}>FIX</span>
                    {r.fix}
                  </div>
                </div>
                <button className="btn btn-ghost" style={{ alignSelf: 'start', fontSize: 11 }} onClick={() => setRoute('script')}>Áp vào kịch bản</button>
              </div>
            ))}
          </div>

          <div style={{
            padding: '16px 20px', background: 'var(--ink)', color: 'var(--canvas)',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12,
          }}>
            <div>
              <div className="mono uc" style={{ fontSize: 9.5, letterSpacing: '0.16em', opacity: 0.5, marginBottom: 4 }}>NẾU ÁP DỤNG 2 FIX CAO</div>
              <div style={{ fontFamily: 'var(--serif)', fontSize: 22, fontWeight: 500 }}>
                Dự đoán ~<span style={{ color: 'rgb(0, 159, 250)' }}>34K view</span> · giữ chân <span style={{ color: 'rgb(0, 159, 250)' }}>56%</span>
              </div>
            </div>
            <button className="btn btn-accent" onClick={() => setRoute('script')}>Viết lại kịch bản → <Icon name="arrow-right" size={11} /></button>
          </div>
        </>
      )}
    </>
  );
}

function SectionMini({ kicker, title }) {
  return (
    <div style={{ marginBottom: 14, paddingBottom: 8, borderBottom: '1px solid var(--ink)' }}>
      <div className="mono uc" style={{ fontSize: 9, color: 'var(--ink-4)', marginBottom: 3 }}>{kicker}</div>
      <h3 className="tight" style={{ margin: 0, fontSize: 22 }}>{title}</h3>
    </div>
  );
}

function Timeline() {
  const segs = [
    { name: 'HOOK',    pct: 5,  color: 'var(--accent)' },
    { name: 'PROMISE', pct: 8,  color: 'var(--ink-2)' },
    { name: 'APP 1',   pct: 14, color: 'var(--ink-3)' },
    { name: 'APP 2',   pct: 14, color: 'var(--ink-2)' },
    { name: 'APP 3',   pct: 14, color: 'var(--ink-3)' },
    { name: 'APP 4',   pct: 14, color: 'var(--ink-2)' },
    { name: 'APP 5',   pct: 16, color: 'var(--ink-3)' },
    { name: 'CTA',     pct: 15, color: 'var(--accent-deep)' },
  ];
  return (
    <div>
      <div style={{ display: 'flex', height: 36, borderRadius: 6, overflow: 'hidden', border: '1px solid var(--rule)' }}>
        {segs.map((s, i) => (
          <div key={i} style={{
            flex: s.pct, background: s.color,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: i === 0 || i === segs.length - 1 ? 'white' : 'var(--canvas)',
            fontSize: 10, fontFamily: 'var(--mono)', fontWeight: 600,
            letterSpacing: '0.05em',
          }}>{s.name}</div>
        ))}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6 }}>
        <span className="mono" style={{ fontSize: 10, color: 'var(--ink-4)' }}>0:00</span>
        <span className="mono" style={{ fontSize: 10, color: 'var(--ink-4)' }}>0:15</span>
        <span className="mono" style={{ fontSize: 10, color: 'var(--ink-4)' }}>0:30</span>
        <span className="mono" style={{ fontSize: 10, color: 'var(--ink-4)' }}>0:45</span>
        <span className="mono" style={{ fontSize: 10, color: 'var(--ink-4)' }}>0:58</span>
      </div>
    </div>
  );
}

window.VideoScreen = VideoScreen;
window.SectionMini = SectionMini;
