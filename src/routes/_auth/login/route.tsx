import { useCallback, useEffect, useRef, useState } from "react";
import {
  Link,
  Navigate,
  useNavigate,
  useSearchParams,
  type MetaFunction,
} from "react-router";
import { motion, AnimatePresence } from "motion/react";
import { ArrowRight, Eye, EyeOff, Lock, Mail } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { supabase } from "@/lib/supabase";

const COPY_BTN_FACEBOOK = "Đăng nhập với Facebook";
const COPY_BTN_GOOGLE = "Đăng nhập với Google";
const COPY_LOADING_FACEBOOK = "Đang kết nối Facebook...";
const COPY_LOADING_GOOGLE = "Đang kết nối Google...";
const COPY_ERROR_OAUTH = "Đăng nhập không thành công — thử lại.";
const COPY_ERROR_FACEBOOK_BLOCKED =
  "Thử đăng nhập bằng Google hoặc mở trong Safari/Chrome.";

export const meta: MetaFunction = () => [
  { title: "Đăng nhập — GetViews" },
  {
    name: "description",
    content: "Data thực từ 46.000+ video TikTok Việt Nam — phân tích video của bạn trong 1 phút.",
  },
];

function FacebookIcon() {
  return (
    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
    </svg>
  );
}

function GoogleIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
      />
      <path
        fill="#34A853"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      />
      <path
        fill="#FBBC05"
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
      />
      <path
        fill="#EA4335"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
      />
    </svg>
  );
}

function Spinner() {
  return (
    <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}

const THUMBS = [
  {
    url: "https://images.unsplash.com/photo-1715114064378-b97c82f06856?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=400",
    rotate: -8,
    x: -52,
    y: 8,
    z: 0,
  },
  {
    url: "https://images.unsplash.com/photo-1665327469792-cf91f5b8d74c?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=400",
    rotate: 0,
    x: 0,
    y: 0,
    z: 1,
  },
  {
    url: "https://images.unsplash.com/photo-1622800371657-4e625b2bd4ea?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=400",
    rotate: 8,
    x: 52,
    y: 8,
    z: 0,
  },
];

type OauthErrorState = {
  target: "facebook" | "google" | "general";
  message: string;
};

export default function LoginRoute() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const callbackErrorHandled = useRef(false);
  const { user, loading: authLoading } = useAuth();
  const [loadingFb, setLoadingFb] = useState(false);
  const [loadingGoogle, setLoadingGoogle] = useState(false);
  const [loadingEmail, setLoadingEmail] = useState(false);
  const [oauthError, setOauthError] = useState<OauthErrorState | null>(null);

  // Email form state
  const [showEmailForm, setShowEmailForm] = useState(false);
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [emailError, setEmailError] = useState("");

  useEffect(() => {
    if (callbackErrorHandled.current) return;
    if (searchParams.get("error") !== "oauth") return;
    callbackErrorHandled.current = true;
    setOauthError({ target: "general", message: COPY_ERROR_OAUTH });
    navigate("/login", { replace: true });
  }, [navigate, searchParams]);

  const redirectTo =
    typeof window !== "undefined" ? `${window.location.origin}/auth/callback` : "/auth/callback";

  const signIn = useCallback(
    async (provider: "facebook" | "google") => {
      if (authLoading || loadingFb || loadingGoogle) return;
      setOauthError(null);
      if (provider === "facebook") setLoadingFb(true);
      else setLoadingGoogle(true);
      const { error } = await supabase.auth.signInWithOAuth({
        provider,
        options: { redirectTo },
      });
      if (error) {
        if (provider === "facebook") setLoadingFb(false);
        else setLoadingGoogle(false);
        const blockedHint =
          provider === "facebook" &&
          /popup|blocked|closed|disallowed|cancel|not\s+allowed|denied/i.test(error.message);
        setOauthError({
          target: provider,
          message: blockedHint ? COPY_ERROR_FACEBOOK_BLOCKED : COPY_ERROR_OAUTH,
        });
      }
    },
    [authLoading, loadingFb, loadingGoogle, redirectTo],
  );

  const handleEmailSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!email || !password) { setEmailError("Vui lòng nhập đầy đủ thông tin."); return; }
      if (password.length < 6) { setEmailError("Mật khẩu ít nhất 6 ký tự."); return; }
      setEmailError("");
      setLoadingEmail(true);
      const { error } = isRegister
        ? await supabase.auth.signUp({ email, password })
        : await supabase.auth.signInWithPassword({ email, password });
      setLoadingEmail(false);
      if (error) {
        setEmailError(error.message);
      } else {
        navigate("/app", { replace: true });
      }
    },
    [email, password, isRegister, navigate],
  );

  const anyLoading = loadingFb || loadingGoogle || loadingEmail;

  if (!authLoading && user) {
    return <Navigate to="/app" replace />;
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4 py-10"
      style={{ background: "var(--background)" }}
    >
      <div className="w-full max-w-[360px] flex flex-col items-center gap-5">
        <motion.div
          initial={{ opacity: 0, y: 18, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
          className="w-full rounded-2xl overflow-hidden"
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            boxShadow: "0 8px 40px 0 rgba(0,0,0,0.18)",
          }}
        >
          <div className="relative h-[168px] flex items-end justify-center mb-2 select-none">
            {THUMBS.map((t, i) => (
              <div
                key={i}
                className="absolute w-[88px] h-[124px] rounded-xl overflow-hidden shadow-xl"
                style={{
                  transform: `rotate(${t.rotate}deg) translateX(${t.x}px) translateY(${t.y}px)`,
                  zIndex: t.z,
                  border: "2px solid rgba(255,255,255,0.08)",
                  bottom: "0",
                }}
              >
                <img src={t.url} alt="" className="w-full h-full object-cover" draggable={false} />
                <div
                  className="absolute inset-0"
                  style={{
                    background: "linear-gradient(to top, rgba(0,0,0,0.45) 0%, transparent 55%)",
                  }}
                />
              </div>
            ))}
          </div>

          <div className="px-6 pt-2 pb-5 text-center">
            <h1 className="gradient-text mb-2 text-xl font-extrabold leading-tight">
              Bắt trend TikTok trước khi nó viral
            </h1>
            <p className="text-sm" style={{ color: "var(--gv-ink-3)", lineHeight: "1.6" }}>
              Data thực từ <strong style={{ color: "var(--ink)" }}>46.000+</strong> video TikTok Việt Nam — phân tích trong{" "}
              <strong style={{ color: "var(--ink)" }}>1 phút</strong>.
            </p>
          </div>

          <div className="px-5 pb-6 flex flex-col gap-2.5">
            {/* Google — primary */}
            <button
              type="button"
              onClick={() => void signIn("google")}
              disabled={anyLoading || authLoading}
              className="w-full flex items-center justify-center gap-2.5 px-4 py-3 rounded-xl text-sm font-semibold transition-all duration-[120ms] active:scale-95 disabled:opacity-60 disabled:cursor-not-allowed"
              style={{ background: "var(--ink)", color: "var(--background)" }}
            >
              {loadingGoogle ? <Spinner /> : <GoogleIcon />}
              {loadingGoogle ? COPY_LOADING_GOOGLE : COPY_BTN_GOOGLE}
            </button>
            {oauthError?.target === "google" ? (
              <p className="text-xs text-center px-1" style={{ color: "var(--danger)" }}>
                {oauthError.message}
              </p>
            ) : null}

            {/* Facebook */}
            <button
              type="button"
              onClick={() => void signIn("facebook")}
              disabled={anyLoading || authLoading}
              className="w-full flex items-center justify-center gap-2.5 px-4 py-3 rounded-xl text-sm font-semibold transition-all duration-[120ms] active:scale-95 disabled:opacity-60 disabled:cursor-not-allowed"
              style={{
                background: "#1877F2",
                color: "#fff",
              }}
            >
              {loadingFb ? <Spinner /> : <FacebookIcon />}
              {loadingFb ? COPY_LOADING_FACEBOOK : COPY_BTN_FACEBOOK}
            </button>
            {oauthError?.target === "facebook" ? (
              <p className="text-xs text-center px-1" style={{ color: "var(--danger)" }}>
                {oauthError.message}
              </p>
            ) : null}

            {oauthError?.target === "general" ? (
              <p className="text-xs text-center px-1" style={{ color: "var(--danger)" }}>
                {oauthError.message}
              </p>
            ) : null}

            {/* Divider */}
            <div className="flex items-center gap-3 my-0.5">
              <div className="flex-1 h-px" style={{ background: "var(--border)" }} />
              <span className="text-[11px] font-semibold" style={{ color: "var(--faint)" }}>HOẶC</span>
              <div className="flex-1 h-px" style={{ background: "var(--border)" }} />
            </div>

            {/* Email toggle button */}
            <button
              type="button"
              onClick={() => setShowEmailForm((v) => !v)}
              disabled={anyLoading}
              className="w-full flex items-center justify-center gap-2.5 px-4 py-3 rounded-xl text-sm font-semibold transition-all duration-[120ms] active:scale-95 disabled:opacity-60 disabled:cursor-not-allowed"
              style={{
                background: "var(--surface-alt)",
                color: "var(--gv-ink-3)",
                border: "1px solid var(--border)",
              }}
            >
              <Mail className="w-4 h-4" strokeWidth={1.8} />
              {showEmailForm ? "Ẩn form đăng nhập" : "Đăng nhập bằng Email"}
            </button>

            {/* Email/Password form */}
            <AnimatePresence initial={false}>
              {showEmailForm && (
                <motion.div
                  key="email-form"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
                  className="overflow-hidden"
                >
                  <form onSubmit={(e) => void handleEmailSubmit(e)} className="flex flex-col gap-2.5 pt-1">
                    {/* Email input */}
                    <div className="relative">
                      <Mail
                        className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 pointer-events-none"
                        style={{ color: "var(--faint)" }}
                        strokeWidth={1.8}
                      />
                      <input
                        type="email"
                        placeholder="Email"
                        value={email}
                        onChange={(e) => { setEmail(e.target.value); setEmailError(""); }}
                        className="w-full pl-9 pr-4 py-3 rounded-xl text-base outline-none transition-all duration-[120ms]"
                        style={{
                          background: "var(--surface-alt)",
                          border: "1px solid var(--border)",
                          color: "var(--ink)",
                        }}
                        onFocus={(e) => (e.currentTarget.style.borderColor = "var(--gv-accent)")}
                        onBlur={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
                      />
                    </div>

                    {/* Password input */}
                    <div className="relative">
                      <Lock
                        className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 pointer-events-none"
                        style={{ color: "var(--faint)" }}
                        strokeWidth={1.8}
                      />
                      <input
                        type={showPw ? "text" : "password"}
                        placeholder="Mật khẩu"
                        value={password}
                        onChange={(e) => { setPassword(e.target.value); setEmailError(""); }}
                        className="w-full pl-9 pr-10 py-3 rounded-xl text-base outline-none transition-all duration-[120ms]"
                        style={{
                          background: "var(--surface-alt)",
                          border: "1px solid var(--border)",
                          color: "var(--ink)",
                        }}
                        onFocus={(e) => (e.currentTarget.style.borderColor = "var(--gv-accent)")}
                        onBlur={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
                      />
                      <button
                        type="button"
                        onClick={() => setShowPw((v) => !v)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 transition-colors duration-[100ms]"
                        style={{ color: "var(--faint)" }}
                        tabIndex={-1}
                      >
                        {showPw
                          ? <EyeOff className="w-4 h-4" strokeWidth={1.8} />
                          : <Eye className="w-4 h-4" strokeWidth={1.8} />
                        }
                      </button>
                    </div>

                    {/* Error */}
                    <AnimatePresence>
                      {emailError && (
                        <motion.p
                          initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                          className="text-xs px-1"
                          style={{ color: "var(--danger)" }}
                        >
                          {emailError}
                        </motion.p>
                      )}
                    </AnimatePresence>

                    {/* Register / Login toggle + forgot */}
                    <div className="flex items-center justify-between px-0.5">
                      <button
                        type="button"
                        onClick={() => setIsRegister((v) => !v)}
                        className="text-xs font-semibold transition-colors duration-[100ms]"
                        style={{ color: "var(--gv-accent)" }}
                      >
                        {isRegister ? "Đã có tài khoản? Đăng nhập" : "Chưa có tài khoản? Đăng ký"}
                      </button>
                      <span className="text-xs" style={{ color: "var(--faint)" }}>
                        Quên mật khẩu?
                      </span>
                    </div>

                    {/* Submit */}
                    <button
                      type="submit"
                      disabled={anyLoading}
                      className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-semibold transition-all duration-[120ms] active:scale-95 disabled:opacity-60 disabled:cursor-not-allowed"
                      style={{ background: "var(--gv-accent)", color: "#fff" }}
                    >
                      {loadingEmail ? (
                        <><Spinner /> Đang xử lý...</>
                      ) : (
                        <>
                          {isRegister ? "Tạo tài khoản" : "Đăng nhập"}
                          <ArrowRight className="w-4 h-4" strokeWidth={2} />
                        </>
                      )}
                    </button>
                  </form>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </motion.div>

        {/* Stats */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3, duration: 0.4 }}
          className="text-xs text-center"
          style={{ color: "var(--faint)" }}
        >
          Đang theo dõi <strong style={{ color: "var(--gv-ink-3)" }}>46.000+</strong> video TikTok Việt Nam
        </motion.p>

        <p className="text-[11px] text-center px-4" style={{ color: "var(--faint)", lineHeight: "1.7" }}>
          Bằng cách đăng nhập, bạn đồng ý với{" "}
          <Link to="#" className="hover:underline" style={{ color: "var(--gv-accent)" }}>
            Điều khoản dịch vụ
          </Link>{" "}
          và{" "}
          <Link to="#" className="hover:underline" style={{ color: "var(--gv-accent)" }}>
            Chính sách bảo mật
          </Link>{" "}
          của GetViews.
        </p>
      </div>
    </div>
  );
}
