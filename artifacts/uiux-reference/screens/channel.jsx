// ============================================================
// Channel deep-dive — Đối Thủ
// ============================================================

function ChannelScreen({ setRoute }) {
  const c = CHANNEL_DETAIL;
  return (
    <div style={{ background: 'var(--canvas)', minHeight: '100%' }}>
      <div style={{ maxWidth: 1280, margin: '0 auto', padding: '24px 28px 80px' }}>
        <button onClick={() => setRoute('home')} className="btn btn-ghost" style={{ marginBottom: 18 }}>
          <Icon name="arrow-left" size={12} /> Về Studio
        </button>

        {/* Hero */}
        <div style={{
          background: 'var(--paper)', border: '1px solid var(--rule)',
          borderRadius: 12, padding: '28px 32px',
          display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 32,
          marginBottom: 28,
        }} className="ch-hero">
          <div>
            <div className="mono uc" style={{ fontSize: 9.5, color: 'var(--ink-4)', marginBottom: 10 }}>HỒ SƠ KÊNH · TECH</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 14 }}>
              <div style={{
                width: 64, height: 64, borderRadius: '50%',
                background: 'var(--accent)', color: 'white',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 22, }}>S</div>
              <div>
                <div className="tight" style={{ fontSize: 38, lineHeight: 1 }}>{c.name}</div>
                <div className="mono" style={{ fontSize: 12, color: 'var(--ink-3)', marginTop: 4 }}>{c.handle} · {c.followers} follower</div>
              </div>
            </div>
            <div className="tight" style={{ fontSize: 18, fontStyle: 'italic', color: 'var(--ink-2)', maxWidth: 460, lineHeight: 1.4 }}>
              "{c.bio}"
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 18, flexWrap: 'wrap' }}>
              <span className="chip">Đăng {c.postingCadence}</span>
              <span className="chip chip-accent">Engagement {c.engagement}</span>
              <span className="chip">{c.totalVideos} video</span>
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 0, alignSelf: 'center', border: '1px solid var(--rule)', borderRadius: 10, overflow: 'hidden' }}>
            {[
              ['VIEW TRUNG BÌNH', c.avgViews, '↑ 12% MoM'],
              ['HOOK CHỦ ĐẠO', `"${c.topHook}"`, '62% video dùng'],
              ['ĐỘ DÀI TỐI ƯU', '42–58s', 'từ 80 video gần'],
              ['THỜI GIAN POST', '7:30 sáng', 'reach +28%'],
            ].map(([l, v, d], i) => (
              <div key={i} style={{
                padding: 18, background: 'var(--canvas)',
                borderRight: i % 2 === 0 ? '1px solid var(--rule)' : 0,
                borderBottom: i < 2 ? '1px solid var(--rule)' : 0,
              }}>
                <div className="mono uc" style={{ fontSize: 9, color: 'var(--ink-4)', marginBottom: 4 }}>{l}</div>
                <div className="tight" style={{ fontSize: 22, lineHeight: 1.1 }}>{v}</div>
                <div className="mono" style={{ fontSize: 10, color: 'var(--pos-deep)', marginTop: 4 }}>{d}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Formula */}
        <div style={{ marginBottom: 36 }}>
          <SectionMini kicker="CÔNG THỨC PHÁT HIỆN" title={`"${c.name} Formula" — 4 bước lặp đi lặp lại`} />
          <div style={{ display: 'flex', height: 80, borderRadius: 8, overflow: 'hidden', border: '1px solid var(--ink)' }}>
            {c.formula.map((s, i) => {
              const colors = ['var(--accent)', 'var(--ink-2)', 'var(--ink-3)', 'var(--accent-deep)'];
              return (
                <div key={i} style={{
                  flex: s.pct, background: colors[i],
                  padding: 12, color: 'white', display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
                }}>
                  <div className="mono uc" style={{ fontSize: 10, opacity: 0.9 }}>{s.step} · {s.pct}%</div>
                  <div style={{ fontSize: 11, lineHeight: 1.3 }}>{s.detail}</div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Two col */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 32 }} className="ch-grid">
          <div>
            <SectionMini kicker="VIDEO ĐỈNH" title="Top 4 video gây tiếng vang" />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              {VIDEOS.slice(0, 4).map(v => (
                <button key={v.id} onClick={() => setRoute('video')} className="tile" style={{ textAlign: 'left' }}>
                  <div style={{ aspectRatio: '9/16', background: v.bg, borderRadius: 6, position: 'relative' }}>
                    <div style={{ position: 'absolute', bottom: 8, left: 10, right: 10, color: 'white' }}>
                      <div className="mono" style={{ fontSize: 10 }}>↑ {v.views}</div>
                    </div>
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--ink-3)', marginTop: 6 }}>{v.title}</div>
                </button>
              ))}
            </div>
          </div>
          <div>
            <SectionMini kicker="ĐIỀU NÊN COPY" title="Học gì từ kênh này" />
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {[
                ['Mở video bằng câu hỏi POV', 'Sammie luôn bắt đầu bằng "Khi bạn ___" — tạo nhận diện ngay 1.5s đầu.'],
                ['Cấu trúc 3 ý + b-roll dày', 'Mỗi video chia 3 ý, mỗi ý ≤8s, b-roll cứ 1.2s đổi cảnh — giữ chân top 5%.'],
                ['CTA mềm dạng câu hỏi', 'Đóng video bằng câu hỏi cộng đồng thay vì "follow tao".'],
                ['Đăng 7:30 sáng', '80% video đều đăng giờ này — reach +28% so với buổi tối.'],
              ].map(([t, b], i) => (
                <div key={i} className="card" style={{ padding: 14, display: 'flex', gap: 12 }}>
                  <div className="mono" style={{ fontSize: 12, color: 'var(--accent-deep)', fontWeight: 600 }}>0{i+1}</div>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 2 }}>{t}</div>
                    <div style={{ fontSize: 12, color: 'var(--ink-3)' }}>{b}</div>
                  </div>
                </div>
              ))}
            </div>
            <button className="btn btn-accent" style={{ marginTop: 16, width: '100%', justifyContent: 'center' }}>
              <Icon name="script" size={13} /> Tạo kịch bản theo công thức này
            </button>
          </div>
        </div>
      </div>

      <style>{`
        @media (max-width: 900px) {
          .ch-hero, .ch-grid { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </div>
  );
}

window.ChannelScreen = ChannelScreen;
