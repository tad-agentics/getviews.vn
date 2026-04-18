// ============================================================
// Onboarding + Settings + Channels list
// ============================================================

function OnboardingScreen({ setRoute }) {
  const [step, setStep] = React.useState(0);
  const [niche, setNiche] = React.useState(null);
  const [comps, setComps] = React.useState([]);

  const finish = () => setRoute('home');

  const canAdvance = step === 0 ? !!niche : comps.length > 0;

  return (
    <div style={{ background: 'var(--canvas)', minHeight: '100vh', display: 'flex' }}>
      {/* Left side editorial */}
      <div style={{ flex: 1, padding: '60px 60px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', borderRight: '1px solid var(--rule)', background: 'var(--canvas-2)' }} className="hide-mobile">
        <div className="mono uc" style={{ fontSize: 10, color: 'var(--ink-4)' }}>
          GETVIEWS · CREATOR STUDIO · SỐ 01
        </div>
        <div>
          <div className="mono uc" style={{ fontSize: 10, color: 'var(--ink-4)', marginBottom: 16 }}>BƯỚC 0{step+1} / 02</div>
          <h1 className="tight" style={{ fontSize: 64, lineHeight: 0.95, margin: 0 }}>
            {step === 0 && <>Bạn đang làm việc với <em>ngách</em> nào?</>}
            {step === 1 && <>Ai là <em>đối thủ tham chiếu</em> của bạn?</>}
          </h1>
          <div style={{ fontSize: 16, color: 'var(--ink-3)', marginTop: 18, maxWidth: 420 }}>
            {step === 0 && 'Chúng tôi sẽ tải về dữ liệu 14 ngày gần nhất của ngách đó — xu hướng, hook, sound, và creator đang nổi.'}
            {step === 1 && 'Chọn 1–3 kênh. Studio sẽ tự cập nhật khi họ post bài mới và so sánh hiệu suất với kênh của bạn.'}
          </div>
        </div>
        <div className="mono uc" style={{ fontSize: 10, color: 'var(--ink-4) ' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <span style={{
              width: 6, height: 6, borderRadius: '50%',
              background: 'var(--accent)',
            }} />
            CREATOR STUDIO · MẤT ~45 GIÂY
          </span>
        </div>
      </div>

      {/* Right side form */}
      <div style={{ flex: 1, padding: '60px 60px', display: 'flex', flexDirection: 'column', justifyContent: 'center', maxWidth: 640 }}>
        {step === 0 && (
          <div>
            <div className="mono uc" style={{ fontSize: 9, color: 'var(--ink-4)', marginBottom: 14 }}>NGÁCH CHÍNH</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              {NICHES.map(n => (
                <button key={n.id} onClick={() => setNiche(n.id)} style={{
                  padding: '14px 16px', textAlign: 'left',
                  border: '1px solid ' + (niche === n.id ? 'var(--ink)' : 'var(--rule)'),
                  background: niche === n.id ? 'var(--ink)' : 'var(--paper)',
                  color: niche === n.id ? 'var(--canvas)' : 'var(--ink)',
                  borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                }}>
                  <span style={{ fontSize: 14 }}>{n.label}</span>
                  <span className="mono" style={{ fontSize: 10, opacity: 0.6 }}>
                    {n.count} video
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        {step === 1 && (
          <div>
            <div className="mono uc" style={{ fontSize: 9, color: 'var(--ink-4)', marginBottom: 14 }}>CHỌN 1–3 KÊNH</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {CREATORS.map(c => {
                const on = comps.includes(c.handle);
                return (
                  <button key={c.handle} onClick={() => setComps(p => on ? p.filter(x => x !== c.handle) : [...p, c.handle].slice(0, 3))} style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '10px 14px',
                    border: '1px solid ' + (on ? 'var(--ink)' : 'var(--rule)'),
                    background: on ? 'var(--canvas-2)' : 'var(--paper)',
                    borderRadius: 8, textAlign: 'left',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <div style={{ width: 16, height: 16, borderRadius: 3, border: '1px solid var(--ink)', background: on ? 'var(--ink)' : 'transparent', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--canvas)' }}>
                        {on && <Icon name="check" size={10} />}
                      </div>
                      <div>
                        <div style={{ fontSize: 13 }}>{c.name}</div>
                        <div className="mono" style={{ fontSize: 10, color: 'var(--ink-4)' }}>{c.handle} · {c.followers}</div>
                      </div>
                    </div>
                    <span className="mono" style={{ fontSize: 10, color: 'var(--accent-deep)' }}>{c.growth}</span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 36 }}>
          <button onClick={() => step > 0 ? setStep(step-1) : setRoute('home')} className="btn btn-ghost">
            <Icon name="arrow-left" size={12} /> Quay lại
          </button>
          <div style={{ display: 'flex', gap: 6 }}>
            {[0,1].map(i => (
              <div key={i} style={{ width: 36, height: 4, borderRadius: 999, background: i <= step ? 'var(--accent)' : 'var(--rule)' }} />
            ))}
          </div>
          <button
            onClick={() => step < 1 ? setStep(step+1) : finish()}
            className="btn"
            disabled={!canAdvance}
            style={!canAdvance ? { opacity: 0.5, cursor: 'not-allowed' } : {}}
          >
            {step === 1 ? 'Vào Creator Studio' : 'Tiếp tục'} <Icon name="arrow-right" size={12} />
          </button>
        </div>
      </div>
    </div>
  );
}

function SettingsScreen() {
  const sections = [
    { id: 'profile', label: 'Hồ Sơ' },
    { id: 'niches', label: 'Ngách & Đối Thủ' },
    { id: 'alerts', label: 'Cảnh Báo' },
    { id: 'export', label: 'Xuất Dữ Liệu' },
    { id: 'billing', label: 'Gói & Thanh Toán' },
    { id: 'team', label: 'Nhóm' },
  ];
  const [active, setActive] = React.useState('profile');
  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: '36px 28px 80px' }}>
      <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr', gap: 36 }} className="settings-layout">
        <aside>
          <div className="mono uc" style={{ fontSize: 9, color: 'var(--ink-4)', marginBottom: 12 }}>CÀI ĐẶT</div>
          <nav style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {sections.map(s => (
              <button key={s.id} onClick={() => setActive(s.id)} style={{
                padding: '10px 12px', borderRadius: 6, textAlign: 'left',
                background: active === s.id ? 'var(--ink)' : 'transparent',
                color: active === s.id ? 'var(--canvas)' : 'var(--ink-2)',
                fontSize: 13, fontWeight: active === s.id ? 600 : 500,
              }}>{s.label}</button>
            ))}
          </nav>
        </aside>
        <div>
          <h1 className="tight" style={{ margin: 0, fontSize: 36, marginBottom: 6 }}>{sections.find(s => s.id === active).label}</h1>
          <hr className="rule" style={{ margin: '18px 0 24px' }} />

          {active === 'profile' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
              <Field label="TÊN HIỂN THỊ" value="An Đỗ" />
              <Field label="EMAIL" value="an@studio.vn" />
              <Field label="HANDLE TIKTOK" value="@an.studio" />
              <Field label="MÚI GIỜ" value="(GMT+7) Việt Nam" />
              <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                <button className="btn">Lưu thay đổi</button>
                <button className="btn btn-ghost">Huỷ</button>
              </div>
            </div>
          )}

          {active === 'niches' && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              {NICHES.slice(0, 6).map(n => (
                <div key={n.id} className="card" style={{ padding: 14, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontSize: 14 }}>{n.label}</div>
                    <div className="mono" style={{ fontSize: 10, color: 'var(--ink-4)' }}>{n.count} video · {n.hot} hot</div>
                  </div>
                  <Toggle on={n.id === 'tech'} />
                </div>
              ))}
            </div>
          )}

          {active === 'alerts' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {[
                ['Hook mới đột phá trong ngách', 'Khi 1 mẫu hook tăng >100% sử dụng tuần', true],
                ['Đối thủ post video viral', 'Khi kênh trong shortlist post bài >2× view trung bình', true],
                ['Báo cáo tuần', 'Email tổng hợp gửi mỗi sáng thứ Hai', false],
                ['Sound đang lên', 'Khi 1 sound được dùng >500 video trong ngách', false],
              ].map(([t, d, on], i) => (
                <div key={i} className="card" style={{ padding: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontSize: 14, marginBottom: 2 }}>{t}</div>
                    <div style={{ fontSize: 12, color: 'var(--ink-3)' }}>{d}</div>
                  </div>
                  <Toggle on={on} />
                </div>
              ))}
            </div>
          )}

          {active === 'billing' && (
            <div className="card" style={{ padding: 24 }}>
              <div className="mono uc" style={{ fontSize: 9, color: 'var(--ink-4)' }}>GÓI HIỆN TẠI</div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, marginTop: 6, marginBottom: 14 }}>
                <div className="tight" style={{ fontSize: 42, lineHeight: 1 }}>Studio Pro</div>
                <div className="mono" style={{ fontSize: 13, color: 'var(--ink-3)' }}>490.000đ / tháng</div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14, marginBottom: 18 }}>
                {[['NGÁCH', '3/3'], ['ĐỐI THỦ', '12/15'], ['KỊCH BẢN AI', '47/100']].map(([l, v]) => (
                  <div key={l}>
                    <div className="mono uc" style={{ fontSize: 9, color: 'var(--ink-4)' }}>{l}</div>
                    <div className="tight" style={{ fontSize: 22 }}>{v}</div>
                  </div>
                ))}
              </div>
              <button className="btn">Nâng cấp lên Studio Plus</button>
            </div>
          )}

          {(active === 'export' || active === 'team') && (
            <div style={{ padding: 40, textAlign: 'center', color: 'var(--ink-4)' }} className="card">
              <div style={{ fontSize: 13 }}>Đang phát triển — sẽ có trong tuần tới.</div>
            </div>
          )}
        </div>
      </div>
      <style>{`@media (max-width: 800px) { .settings-layout { grid-template-columns: 1fr !important; } }`}</style>
    </div>
  );
}

function Field({ label, value }) {
  return (
    <div>
      <div className="mono uc" style={{ fontSize: 9, color: 'var(--ink-4)', marginBottom: 6 }}>{label}</div>
      <input defaultValue={value} style={{
        width: '100%', padding: '10px 14px',
        border: '1px solid var(--rule)', borderRadius: 6,
        background: 'var(--paper)', fontSize: 14,
      }} />
    </div>
  );
}

function Toggle({ on: initial }) {
  const [on, setOn] = React.useState(initial);
  return (
    <button onClick={() => setOn(o => !o)} style={{
      width: 38, height: 22, borderRadius: 999,
      background: on ? 'var(--accent)' : 'var(--rule)',
      position: 'relative', transition: 'background 0.15s ease',
    }}>
      <div style={{
        position: 'absolute', top: 2, left: on ? 18 : 2,
        width: 18, height: 18, borderRadius: '50%',
        background: 'white', transition: 'left 0.15s ease',
        boxShadow: '0 1px 2px rgba(0,0,0,0.2)',
      }} />
    </button>
  );
}

window.OnboardingScreen = OnboardingScreen;
window.SettingsScreen = SettingsScreen;
