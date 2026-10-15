"use client";
import * as React from "react";
import { Label } from "./label";
import { cn } from "@/lib/utils";

/**
 * Nhãn, mô tả và lỗi của một trường, liên kết bằng aria-describedby để công nghệ hỗ trợ đọc được
 * (SRS mục 3.5.1: lỗi hiển thị tại trường, giữ tới khi sửa hợp lệ). Truyền đúng một control làm children.
 */
function FormField({
  label, description, error, className, children,
}: { label: string; description?: string; error?: string; className?: string; children: React.ReactElement<Record<string, unknown>> }) {
  const id = React.useId();
  const controlId = (children.props.id as string) || `${id}-control`;
  const describedBy = [description ? `${id}-description` : null, error ? `${id}-error` : null].filter(Boolean).join(" ") || undefined;
  return (
    <div className={cn("grid gap-2", className)}>
      <Label htmlFor={controlId}>{label}</Label>
      {React.cloneElement(children, { id: controlId, "aria-describedby": describedBy, "aria-invalid": error ? true : undefined })}
      {description && <p id={`${id}-description`} className="text-xs text-muted-foreground">{description}</p>}
      {error && <p id={`${id}-error`} className="text-sm text-status-failed">{error}</p>}
    </div>
  );
}

export { FormField };
