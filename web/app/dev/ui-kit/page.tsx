import type { Metadata } from "next";
import { UiKitGallery } from "./gallery";

export const metadata: Metadata = { title: "UI kit - InsightHub" };

// Trang tham khảo cho người phát triển: xem toàn bộ component nền và trạng thái. Không phải màn hình sản phẩm.
export default function UiKitPage() {
  return (
    <div className="grid gap-6">
      <div className="grid gap-1">
        <h1 className="text-2xl font-semibold">UI kit</h1>
        <p className="text-sm text-muted-foreground">Component nền dùng chung (components/ui). Hướng dẫn: docs/UI_Foundation.md.</p>
      </div>
      <UiKitGallery />
    </div>
  );
}
