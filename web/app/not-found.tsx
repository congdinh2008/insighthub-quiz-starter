import Link from "next/link";
import { EmptyState } from "@/components/ui/feedback";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <EmptyState
      className="mx-auto mt-10 max-w-lg"
      title="Không tìm thấy trang"
      description="Đường dẫn không tồn tại hoặc bạn không có quyền truy cập."
      action={<Button asChild variant="outline"><Link href="/">Về trang chính</Link></Button>}
    />
  );
}
