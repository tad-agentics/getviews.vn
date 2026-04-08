import type { MetaFunction } from "react-router";

export const meta: MetaFunction = () => [
  { title: "Đăng nhập — GetViews.vn" },
];

export default function LoginPage() {
  return (
    <main>
      {/* Login screen — built in /foundation by Frontend Developer */}
      <p>Đăng nhập</p>
    </main>
  );
}
