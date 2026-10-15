"use client";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "./button";

/** Phân trang theo con trỏ (cursor): API trả trang tiếp theo, giao diện không tự suy ra tổng số trang. */
export function CursorPagination({ hasPrevious, hasNext, onPrevious, onNext, label = "Phân trang" }: {
  hasPrevious: boolean; hasNext: boolean; onPrevious: () => void; onNext: () => void; label?: string;
}) {
  return (
    <nav aria-label={label} className="flex items-center justify-end gap-2">
      <Button variant="outline" size="sm" onClick={onPrevious} disabled={!hasPrevious}><ChevronLeft aria-hidden="true" />Trang trước</Button>
      <Button variant="outline" size="sm" onClick={onNext} disabled={!hasNext}>Trang sau<ChevronRight aria-hidden="true" /></Button>
    </nav>
  );
}
