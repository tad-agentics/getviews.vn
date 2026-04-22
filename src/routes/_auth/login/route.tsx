import { useCallback, useEffect, useRef, useState } from "react";
import {
  Link,
  Navigate,
  useNavigate,
  useSearchParams,
  type MetaFunction,
} from "react-router";
import { motion, AnimatePresence } from "motion/react";
import { ArrowRight, Eye, EyeOff, Loader2, Lock, Mail } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { supabase } from "@/lib/supabase";
import { Input } from "@/components/ui/Input";
import { Btn } from "@/components/v2/Btn";
import { cn } from "@/components/ui/utils";

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
    <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
    </svg>
  );
}

function GoogleIcon() {
  // Brand identity colours — Google's Material Brand Guidelines mandate
  // the four "G" facet hex values. Intentional exception to the
  // ``--gv-*`` token rule; do NOT swap for theme tokens or the icon
  // becomes legally non-compliant with Google's brand asset terms.
  return (
    <svg className="h-4 w-4" viewBox="0 0 24 24" aria-hidden="true">
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

/** Full-width OAuth / email actions — Studio radius + focus ring (matches v2/Btn focus). */
const fullWidthAction =
  "flex w-full items-center justify-center gap-2.5 rounded-[var(--gv-radius-md)] px-4 py-3 text-sm font-semibold " +
  "transition-all duration-150 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60 " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--gv-accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--gv-canvas)]";

export default function LoginRoute() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const callbackErrorHandled = useRef(false);
  const { user, loading: authLoading } = useAuth();
  const [loadingFb, setLoadingFb] = useState(false);
  const [loadingGoogle, setLoadingGoogle] = useState(false);
  const [loadingEmail, setLoadingEmail] = useState(false);
  const [oauthError, setOauthError] = useState<OauthErrorState | null>(null);

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
      if (!email || !password) {
        setEmailError("Vui lòng nhập đầy đủ thông tin.");
        return;
      }
      if (password.length < 6) {
        setEmailError("Mật khẩu ít nhất 6 ký tự.");
        return;
      }
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

  const inputFieldClass =
    "rounded-[var(--gv-radius-md)] border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] py-3 pl-9 pr-4 text-base text-[color:var(--gv-ink)] " +
    "placeholder:text-[color:var(--gv-ink-4)] focus:border-[color:var(--gv-accent)] focus:ring-1 focus:ring-[color:var(--gv-accent)]";

  return (
    <div className="gv-studio-type flex min-h-screen items-center justify-center bg-[color:var(--gv-canvas)] px-4 py-10 text-[color:var(--gv-ink)]">
      <div className="flex w-full max-w-[360px] flex-col items-center gap-5">
        <motion.div
          initial={{ opacity: 0, y: 18, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
          className="w-full overflow-hidden rounded-[var(--gv-radius-lg)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] shadow-[0_8px_40px_-12px_rgb(10_12_16/0.1)]"
        >
          <div className="relative mb-2 flex h-[168px] select-none items-end justify-center">
            {THUMBS.map((t, i) => (
              <div
                key={i}
                className="absolute h-[124px] w-[88px] overflow-hidden rounded-[var(--gv-radius-md)] border-2 border-white/10 shadow-xl"
                style={{
                  transform: `rotate(${t.rotate}deg) translateX(${t.x}px) translateY(${t.y}px)`,
                  zIndex: t.z,
                  bottom: "0",
                }}
              >
                <img src={t.url} alt="" className="h-full w-full object-cover" draggable={false} />
                <div className="absolute inset-0 bg-gradient-to-t from-[rgb(10_12_16/0.45)] to-transparent" />
              </div>
            ))}
          </div>

          <div className="px-6 pb-5 pt-2 text-center">
            <h1 className="gradient-text mb-2 text-xl font-extrabold leading-tight">
              Bắt trend TikTok trước khi nó viral
            </h1>
            <p className="text-sm leading-relaxed text-[color:var(--gv-ink-3)]">
              Data thực từ <strong className="text-[color:var(--gv-ink)]">46.000+</strong> video TikTok Việt Nam — phân tích trong{" "}
              <strong className="text-[color:var(--gv-ink)]">1 phút</strong>.
            </p>
          </div>

          <div className="flex flex-col gap-2.5 px-5 pb-6">
            <button
              type="button"
              onClick={() => void signIn("google")}
              disabled={anyLoading || authLoading}
              className={cn(
                fullWidthAction,
                "bg-[color:var(--gv-ink)] text-[color:var(--gv-canvas)] hover:opacity-95",
              )}
            >
              {loadingGoogle ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <GoogleIcon />
              )}
              {loadingGoogle ? COPY_LOADING_GOOGLE : COPY_BTN_GOOGLE}
            </button>
            {oauthError?.target === "google" ? (
              <p className="px-1 text-center text-xs text-[color:var(--gv-danger)]">{oauthError.message}</p>
            ) : null}

            {/* Facebook — brand colour ``#1877F2`` is Meta's mandated
                Facebook Blue. Intentional exception to the ``--gv-*``
                token rule per the same brand-asset reasoning as the
                Google icon above (Meta brand guidelines). */}
            <button
              type="button"
              onClick={() => void signIn("facebook")}
              disabled={anyLoading || authLoading}
              className={cn(fullWidthAction, "bg-[#1877F2] text-white hover:opacity-95")}
            >
              {loadingFb ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <FacebookIcon />
              )}
              {loadingFb ? COPY_LOADING_FACEBOOK : COPY_BTN_FACEBOOK}
            </button>
            {oauthError?.target === "facebook" ? (
              <p className="px-1 text-center text-xs text-[color:var(--gv-danger)]">{oauthError.message}</p>
            ) : null}

            {oauthError?.target === "general" ? (
              <p className="px-1 text-center text-xs text-[color:var(--gv-danger)]">{oauthError.message}</p>
            ) : null}

            <div className="my-0.5 flex items-center gap-3">
              <div className="h-px flex-1 bg-[color:var(--gv-rule)]" />
              <span className="text-[11px] font-semibold tracking-wide text-[color:var(--gv-ink-4)]">HOẶC</span>
              <div className="h-px flex-1 bg-[color:var(--gv-rule)]" />
            </div>

            <button
              type="button"
              onClick={() => setShowEmailForm((v) => !v)}
              disabled={anyLoading}
              className={cn(
                fullWidthAction,
                "border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-ink-3)] hover:bg-[color:var(--gv-rule-2)]",
              )}
            >
              <Mail className="h-4 w-4" strokeWidth={1.8} aria-hidden />
              {showEmailForm ? "Ẩn form đăng nhập" : "Đăng nhập bằng Email"}
            </button>

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
                    <div className="relative">
                      <Mail
                        className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[color:var(--gv-ink-4)]"
                        strokeWidth={1.8}
                        aria-hidden
                      />
                      <Input
                        type="email"
                        placeholder="Email của bạn"
                        value={email}
                        onChange={(e) => {
                          setEmail(e.target.value);
                          setEmailError("");
                        }}
                        className={inputFieldClass}
                        autoComplete="email"
                      />
                    </div>

                    <div className="relative">
                      <Lock
                        className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[color:var(--gv-ink-4)]"
                        strokeWidth={1.8}
                        aria-hidden
                      />
                      <Input
                        type={showPw ? "text" : "password"}
                        placeholder="Mật khẩu"
                        value={password}
                        onChange={(e) => {
                          setPassword(e.target.value);
                          setEmailError("");
                        }}
                        className={cn(inputFieldClass, "pr-10")}
                        autoComplete={isRegister ? "new-password" : "current-password"}
                      />
                      <button
                        type="button"
                        onClick={() => setShowPw((v) => !v)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-[color:var(--gv-ink-4)] transition-colors hover:text-[color:var(--gv-ink-3)]"
                        tabIndex={-1}
                        aria-label={showPw ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                      >
                        {showPw ? (
                          <EyeOff className="h-4 w-4" strokeWidth={1.8} />
                        ) : (
                          <Eye className="h-4 w-4" strokeWidth={1.8} />
                        )}
                      </button>
                    </div>

                    <AnimatePresence>
                      {emailError && (
                        <motion.p
                          initial={{ opacity: 0, y: -4 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0 }}
                          className="px-1 text-xs text-[color:var(--gv-danger)]"
                        >
                          {emailError}
                        </motion.p>
                      )}
                    </AnimatePresence>

                    <div className="flex items-center justify-between px-0.5">
                      <button
                        type="button"
                        onClick={() => setIsRegister((v) => !v)}
                        className="text-xs font-semibold text-[color:var(--gv-accent)] transition-colors hover:text-[color:var(--gv-accent-deep)]"
                      >
                        {isRegister ? "Đã có tài khoản? Đăng nhập" : "Chưa có tài khoản? Đăng ký"}
                      </button>
                      <span className="text-xs text-[color:var(--gv-ink-4)]">Quên mật khẩu?</span>
                    </div>

                    <Btn
                      type="submit"
                      variant="accent"
                      size="lg"
                      disabled={anyLoading}
                      className="h-auto w-full justify-center gap-2 rounded-[var(--gv-radius-md)] py-3"
                    >
                      {loadingEmail ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                          Đang xử lý...
                        </>
                      ) : (
                        <>
                          {isRegister ? "Tạo tài khoản" : "Đăng nhập"}
                          <ArrowRight className="h-4 w-4" strokeWidth={2} aria-hidden />
                        </>
                      )}
                    </Btn>
                  </form>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3, duration: 0.4 }}
          className="text-center text-xs text-[color:var(--gv-ink-4)]"
        >
          Đang theo dõi <strong className="text-[color:var(--gv-ink-3)]">46.000+</strong> video TikTok Việt Nam
        </motion.p>

        <p className="px-4 text-center text-[11px] leading-relaxed text-[color:var(--gv-ink-4)]">
          Bằng cách đăng nhập, bạn đồng ý với{" "}
          <Link to="#" className="text-[color:var(--gv-accent)] hover:underline">
            Điều khoản dịch vụ
          </Link>{" "}
          và{" "}
          <Link to="#" className="text-[color:var(--gv-accent)] hover:underline">
            Chính sách bảo mật
          </Link>{" "}
          của GetViews.
        </p>
      </div>
    </div>
  );
}
