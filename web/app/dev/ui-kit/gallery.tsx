"use client";
import { useState } from "react";
import { FileText, Plus } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Alert, EmptyState, Skeleton, Spinner } from "@/components/ui/feedback";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import { CursorPagination } from "@/components/ui/pagination";
import { StatusBadge } from "@/components/ui/status-badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/toast";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader><CardTitle>{title}</CardTitle></CardHeader>
      <CardContent className="flex flex-wrap items-start gap-3">{children}</CardContent>
    </Card>
  );
}

export function UiKitGallery() {
  const notify = useToast();
  const [page, setPage] = useState(1);
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Section title="Button">
        <Button>Mặc định</Button>
        <Button variant="secondary">Phụ</Button>
        <Button variant="outline">Viền</Button>
        <Button variant="destructive">Xóa</Button>
        <Button variant="ghost">Ghost</Button>
        <Button loading>Đang gửi</Button>
        <Button size="icon" aria-label="Tạo mới"><Plus aria-hidden="true" /></Button>
      </Section>
      <Section title="Trạng thái">
        {(["Pending", "Processing", "Ready", "Succeeded", "NoEvidence", "Failed"] as const).map(status => <StatusBadge key={status} status={status} />)}
        <Badge variant="secondary">Badge</Badge>
      </Section>
      <Section title="Form">
        <div className="grid w-full gap-4">
          <FormField label="Tên" description="Từ 1 đến 120 ký tự."><Input placeholder="Ví dụ: Quy trình nội bộ" /></FormField>
          <FormField label="Mô tả" error="Mô tả vượt giới hạn cho phép."><Textarea defaultValue="Nội dung quá dài" /></FormField>
        </div>
      </Section>
      <Section title="Hộp thoại">
        <Dialog>
          <DialogTrigger asChild><Button variant="outline">Mở hộp thoại</Button></DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Tiêu đề hộp thoại</DialogTitle>
              <DialogDescription>Focus nằm trong hộp thoại, Escape để đóng, focus trở lại nút mở.</DialogDescription>
            </DialogHeader>
            <DialogFooter><Button>Lưu</Button></DialogFooter>
          </DialogContent>
        </Dialog>
        <ConfirmDialog
          trigger={<Button variant="destructive">Xóa mục mẫu</Button>}
          title="Xóa mục mẫu?"
          description="Nêu rõ đối tượng, dữ liệu bị ảnh hưởng và khả năng khôi phục."
          confirmLabel="Xóa"
          destructive
          onConfirm={() => notify("Đã xóa mục mẫu.")}
        />
        <Button variant="secondary" onClick={() => notify("Đã lưu thay đổi.")}>Hiện toast</Button>
      </Section>
      <Section title="Thông báo tại chỗ">
        <div className="grid w-full gap-3">
          <Alert title="Tài liệu đang được xử lý." />
          <Alert variant="warning" title="Đã đạt giới hạn.">Xóa bớt mục không cần thiết để tạo mới.</Alert>
          <Alert variant="error" title="Không lưu được." action={<Button size="sm" variant="outline">Thử lại</Button>}>Kiểm tra kết nối rồi thử lại.</Alert>
        </div>
      </Section>
      <Section title="Đang tải và danh sách rỗng">
        <div className="grid w-full gap-3">
          <Spinner label="Đang tải danh sách" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-3/4" />
          <EmptyState icon={FileText} title="Chưa có mục nào" description="Tạo mục đầu tiên để bắt đầu." action={<Button size="sm">Tạo mới</Button>} />
        </div>
      </Section>
      <Section title="Tabs và phân trang">
        <Tabs defaultValue="a" className="w-full">
          <TabsList><TabsTrigger value="a">Tab A</TabsTrigger><TabsTrigger value="b">Tab B</TabsTrigger></TabsList>
          <TabsContent value="a"><p className="text-sm text-muted-foreground">Nội dung A. Phím mũi tên chuyển tab.</p></TabsContent>
          <TabsContent value="b"><p className="text-sm text-muted-foreground">Nội dung B.</p></TabsContent>
        </Tabs>
        <div className="w-full">
          <p className="mb-2 text-sm text-muted-foreground">Trang {page}</p>
          <CursorPagination hasPrevious={page > 1} hasNext={page < 3} onPrevious={() => setPage(page - 1)} onNext={() => setPage(page + 1)} />
        </div>
      </Section>
      <Section title="Card">
        <Card className="w-full">
          <CardHeader><CardTitle>Tiêu đề thẻ</CardTitle><CardDescription>Mô tả ngắn của thẻ.</CardDescription></CardHeader>
          <CardContent><p className="text-sm">Nội dung thẻ.</p></CardContent>
        </Card>
      </Section>
    </div>
  );
}
