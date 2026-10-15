"use client";
import { Alert } from "@/components/ui/feedback";
import { Button } from "@/components/ui/button";

// Lỗi không mong đợi khi hiển thị trang: không lộ thông tin nội bộ, cho phép thử lại (IH-UX-004-AC02).
export default function Error({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="mx-auto max-w-lg py-10">
      <Alert variant="error" title="Không hiển thị được trang này." action={<Button onClick={reset}>Thử lại</Button>}>
        Hãy thử lại. Nếu lỗi lặp lại, ghi thời điểm và thao tác vừa làm để kiểm tra nhật ký.
      </Alert>
    </div>
  );
}
