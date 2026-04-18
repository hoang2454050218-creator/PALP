"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { GraduationCap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";
import { ApiError } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const usernameRef = useRef<HTMLInputElement>(null);

  // Programmatic focus on mount keeps the UX of "click → start typing"
  // without violating jsx-a11y/no-autofocus (which warns about screen
  // readers losing context when the page autoFocus jumps unexpectedly).
  useEffect(() => {
    const t = window.setTimeout(() => usernameRef.current?.focus(), 0);
    return () => window.clearTimeout(t);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await login(username.trim(), password);
      const user = useAuth.getState().user;
      router.push(user?.role === "lecturer" || user?.role === "admin" ? "/overview" : "/dashboard");
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 401 || err.status === 400) {
          setError("Tên đăng nhập hoặc mật khẩu không đúng. Vui lòng kiểm tra lại.");
        } else if (err.status === 429) {
          setError("Quá nhiều lần thử đăng nhập. Vui lòng thử lại sau ít phút.");
        } else if (err.isServerError() || err.isNetwork()) {
          setError("Không thể kết nối tới máy chủ. Vui lòng thử lại sau.");
        } else {
          setError(err.detail || "Đăng nhập không thành công.");
        }
      } else {
        setError("Đã xảy ra lỗi không mong muốn. Vui lòng thử lại.");
      }
    } finally {
      setLoading(false);
    }
  };

  const hasError = error.length > 0;

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-primary/5 via-background to-info/10 p-4">
      <Card className="w-full max-w-md shadow-xl">
        <CardHeader className="text-center space-y-4">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
            <GraduationCap className="h-9 w-9 text-primary" aria-hidden="true" />
          </div>
          <div>
            <CardTitle className="text-2xl">PALP</CardTitle>
            <CardDescription className="mt-2">
              Personalized Adaptive Learning Platform
              <br />
              <span className="text-xs">ĐH Kiến trúc Đà Nẵng</span>
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            {hasError && (
              <div
                className="rounded-md bg-destructive/10 p-3 text-sm text-destructive"
                role="alert"
                id="login-error"
              >
                {error}
              </div>
            )}
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="username">
                Tên đăng nhập
              </label>
              <Input
                ref={usernameRef}
                id="username"
                placeholder="Nhập tên đăng nhập"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoComplete="username"
                aria-invalid={hasError || undefined}
                aria-describedby={hasError ? "login-error" : undefined}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="password">
                Mật khẩu
              </label>
              <Input
                id="password"
                type="password"
                placeholder="Nhập mật khẩu"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                aria-invalid={hasError || undefined}
                aria-describedby={hasError ? "login-error" : undefined}
              />
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Đang đăng nhập..." : "Đăng nhập"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
