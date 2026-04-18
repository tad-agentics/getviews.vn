// ============================================================
// Shell — sidebar, topbar, route container
// ============================================================

function Sidebar({ route, setRoute, collapsed }) {
  const nav = [
    { id: 'home',     label: 'Studio',         icon: 'chat' },
    { id: 'trends',   label: 'Xu Hướng',       icon: 'trend' },
    { id: 'kol',      label: 'Kênh Tham Chiếu', icon: 'eye' },
    { id: 'script',   label: 'Kịch Bản',       icon: 'script' },
  ];

  if (collapsed) return null;

  return (
    <aside style={{
      width: 240, flexShrink: 0,
      borderRight: '1px solid var(--rule)',
      background: 'var(--canvas-2)',
      display: 'flex', flexDirection: 'column',
      height: '100vh', position: 'sticky', top: 0,
    }}>
      {/* Brand */}
      <div style={{ padding: '20px 20px 18px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 30, height: 30, background: 'var(--ink)',
            borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: 'var(--accent)',
          }}>
            <Icon name="logo" size={18} />
          </div>
          <div style={{ lineHeight: 1 }}>
            <div className="tight" style={{ fontSize: 20, letterSpacing: '-0.04em', fontWeight: 700 }}>
              Getviews<span style={{ color: 'var(--accent-2-deep)' }}>.</span>
            </div>
            <div className="mono uc" style={{ fontSize: 9, color: 'var(--ink-4)', marginTop: 2, fontWeight: 600 }}>
              Studio · Creator
            </div>
          </div>
        </div>
        <button className="btn-ghost" style={{
          width: 28, height: 28, border: '1px solid var(--rule)',
          borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'var(--paper)',
        }} title="Cuộc trò chuyện mới">
          <Icon name="plus" size={14} />
        </button>
      </div>

      <hr className="rule" />

      {/* Primary nav */}
      <nav style={{ padding: '12px 12px', display: 'flex', flexDirection: 'column', gap: 2 }}>
        {nav.map(n => (
          <button
            key={n.id}
            onClick={() => setRoute(n.id)}
            style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '9px 12px', borderRadius: 6,
              fontSize: 13, fontWeight: route === n.id ? 600 : 500,
              color: route === n.id ? 'var(--canvas)' : 'var(--ink-2)',
              background: route === n.id ? 'var(--ink)' : 'transparent',
              textAlign: 'left',
              transition: 'background 0.15s ease',
            }}
            onMouseEnter={e => { if (route !== n.id) e.currentTarget.style.background = 'rgba(20,17,12,0.05)'; }}
            onMouseLeave={e => { if (route !== n.id) e.currentTarget.style.background = 'transparent'; }}
          >
            <Icon name={n.icon} size={15} />
            <span style={{ whiteSpace: 'nowrap' }}>{n.label}</span>
          </button>
        ))}
      </nav>

      <hr className="rule" />

      {/* Pinned niches */}
      <div style={{ padding: '14px 16px 10px' }}>
        <div className="mono uc" style={{ fontSize: 9, color: 'var(--ink-4)', marginBottom: 10 }}>
          Ngách Của Bạn
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {NICHES.slice(0, 3).map(n => (
            <div key={n.id} style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '7px 10px', borderRadius: 6, fontSize: 12,
              cursor: 'pointer',
            }}
              onMouseEnter={e => e.currentTarget.style.background = 'rgba(20,17,12,0.04)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >
              <span style={{ color: 'var(--ink-2)' }}>{n.label}</span>
              <span className="mono" style={{ fontSize: 10, color: 'var(--pos-deep)' }}>↑{n.hot}</span>
            </div>
          ))}
        </div>
      </div>

      <hr className="rule" />

      {/* Recent chats / campaigns */}
      <div style={{ padding: '14px 16px 10px', flex: 1, overflowY: 'auto', minHeight: 0 }}>
        <div className="mono uc" style={{ fontSize: 9, color: 'var(--ink-4)', marginBottom: 10 }}>
          Gần Đây
        </div>
        <RecentList />
      </div>

      {/* Footer */}
      <div style={{
        padding: '10px 12px',
        borderTop: '1px solid var(--rule)',
        display: 'flex', flexDirection: 'column', gap: 8,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <button onClick={() => setRoute('settings')} style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '6px 8px', borderRadius: 6, fontSize: 12, color: 'var(--ink-3)',
          }}>
            <Icon name="settings" size={14} />
            <span>Cài đặt</span>
          </button>
          <div style={{
            width: 28, height: 28, borderRadius: '50%',
            background: 'var(--accent)', color: 'white',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 11, fontWeight: 600,
          }}>AD</div>
        </div>
      </div>
    </aside>
  );
}

// ============================================================
// Top bar — context-aware breadcrumb + actions
// ============================================================
function TopBar({ route, setRoute, onToggleSidebar }) {
  const titles = {
    home:     { kicker: 'STUDIO',      title: 'Sảnh Sáng Tạo' },
    trends:   { kicker: 'BÁO CÁO',     title: 'Xu Hướng Tuần Này' },
    channels: { kicker: 'PHÂN TÍCH',   title: 'Đối Thủ' },
    kol:      { kicker: 'THEO DÕI',    title: 'Kênh Tham Chiếu' },
    script:   { kicker: 'XƯỞNG VIẾT',  title: 'Kịch Bản' },
    video:    { kicker: 'BÁO CÁO',     title: 'Phân Tích Video' },
    channel:  { kicker: 'BÁO CÁO',     title: 'Phân Tích Kênh' },
    settings: { kicker: 'TÀI KHOẢN',   title: 'Cài Đặt' },
    answer:   { kicker: 'NGHIÊN CỨU',  title: 'Báo Cáo Nghiên Cứu' },
    onboarding: { kicker: 'BẮT ĐẦU',   title: 'Chào Mừng' },
  };
  const t = titles[route] || titles.home;

  return (
    <header style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '14px 28px',
      borderBottom: '1px solid var(--rule)',
      background: 'var(--canvas)',
      position: 'sticky', top: 0, zIndex: 10,
      minHeight: 64,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <button onClick={onToggleSidebar} className="hide-mobile" style={{
          width: 32, height: 32, border: '1px solid var(--rule)',
          borderRadius: 6, display: 'none',
        }}>
          <Icon name="menu" size={14} />
        </button>
        <div>
          <div className="mono uc" style={{ fontSize: 9.5, color: 'var(--ink-4)', marginBottom: 3 }}>
            {t.kicker}
          </div>
          <div className="tight" style={{ fontSize: 24, lineHeight: 1, color: 'var(--ink)', letterSpacing: '-0.03em', fontWeight: 600 }}>
            {t.title}
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div className="hide-narrow" style={{
          display: 'flex', alignItems: 'center', gap: 6,
          padding: '6px 12px', borderRadius: 999,
          background: 'var(--paper)', border: '1px solid var(--rule)',
          fontSize: 11, color: 'var(--ink-3)',
          whiteSpace: 'nowrap',
        }}>
          <span className="live-dot"></span>
          <span className="mono">DỮ LIỆU CẬP NHẬT 2 PHÚT TRƯỚC</span>
        </div>
        <button className="btn btn-ghost hide-mobile" style={{ whiteSpace: 'nowrap' }}>
          <Icon name="bookmark" size={13} />
          <span>Đã Lưu</span>
        </button>
        <button className="btn" style={{ whiteSpace: 'nowrap' }}>
          <Icon name="plus" size={13} />
          <span>Phân tích mới</span>
        </button>
      </div>
    </header>
  );
}

window.Sidebar = Sidebar;
window.TopBar = TopBar;

// ============================================================
// Recent list — local state w/ per-item delete on hover
// ============================================================
function RecentList() {
  const seed = RECENT_CHATS;
  const storageKey = 'gv-recent-creator-deleted';
  const [deleted, setDeleted] = React.useState(() => {
    try { return JSON.parse(localStorage.getItem(storageKey) || '[]'); }
    catch { return []; }
  });
  const [hoverId, setHoverId] = React.useState(null);

  const remove = (id) => {
    const next = [...deleted, id];
    setDeleted(next);
    try { localStorage.setItem(storageKey, JSON.stringify(next)); } catch {}
  };
  const restoreAll = () => {
    setDeleted([]);
    try { localStorage.removeItem(storageKey); } catch {}
  };

  const items = seed.filter(c => !deleted.includes(c.id));

  if (items.length === 0) {
    return (
      <div style={{
        padding: '14px 10px', fontSize: 11, color: 'var(--ink-4)',
        textAlign: 'left', lineHeight: 1.5,
      }}>
        Không còn mục nào.{' '}
        <button onClick={restoreAll} style={{
          color: 'var(--accent-deep)', textDecoration: 'underline', fontSize: 11,
        }}>Khôi phục</button>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {items.map(c => {
        const hovered = hoverId === c.id;
        return (
          <div key={c.id} style={{
            padding: '7px 10px', borderRadius: 6, fontSize: 12,
            color: 'var(--ink-2)', cursor: 'pointer', position: 'relative',
            display: 'flex', alignItems: 'flex-start', gap: 8,
            background: hovered ? 'rgba(20,17,12,0.04)' : 'transparent',
            transition: 'background 0.1s',
          }}
            onMouseEnter={() => setHoverId(c.id)}
            onMouseLeave={() => setHoverId(null)}
          >
            <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 2 }}>
              <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {c.title}
              </div>
              <div className="mono" style={{ fontSize: 9, color: 'var(--ink-4)' }}>{c.when}</div>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); remove(c.id); }}
              aria-label="Xoá khỏi Gần Đây"
              title="Xoá"
              style={{
                width: 22, height: 22, borderRadius: 4,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: 'var(--ink-4)',
                background: 'transparent',
                opacity: hovered ? 1 : 0,
                transition: 'opacity 0.1s, background 0.1s, color 0.1s',
                flexShrink: 0, marginTop: -1,
              }}
              onMouseEnter={e => {
                e.currentTarget.style.background = 'var(--accent-soft)';
                e.currentTarget.style.color = 'var(--accent-deep)';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background = 'transparent';
                e.currentTarget.style.color = 'var(--ink-4)';
              }}
            >
              <Icon name="x" size={11} />
            </button>
          </div>
        );
      })}
    </div>
  );
}

window.RecentList = RecentList;
