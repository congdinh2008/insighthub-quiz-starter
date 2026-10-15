"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import { Alert } from "@/components/ui/feedback";
import { authClient } from "@/lib/auth/client";
import { clearClientState } from "@/lib/client-state";

export function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const { error: failure } = await authClient.signIn.email({ email, password });
    setBusy(false);
    if (failure) {
      // Cùng một thông báo cho sai email và sai mật khẩu, không tiết lộ tài khoản tồn tại.
      setError("Email hoặc mật khẩu không đúng.");
      return;
    }
    clearClientState();
    router.push("/");
    router.refresh();
  }

  return (
    <form onSubmit={submit} className="grid gap-4" noValidate>
      {error && <Alert variant="error" title={error} />}
      <FormField label="Email">
        <Input type="email" autoComplete="email" required value={email} onChange={e => setEmail(e.target.value)} />
      </FormField>
      <FormField label="Mật khẩu">
        <Input type="password" autoComplete="current-password" required value={password} onChange={e => setPassword(e.target.value)} />
      </FormField>
      <Button type="submit" loading={busy}>Đăng nhập</Button>
    </form>
  );
}
