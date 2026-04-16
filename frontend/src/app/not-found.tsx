import { FileQuestion, Home } from "lucide-react";
import { Button } from "@/components/ui/button";
import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="text-center max-w-md">
        <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-muted">
          <FileQuestion className="h-10 w-10 text-muted-foreground" aria-hidden="true" />
        </div>
        <h1 className="text-2xl font-bold mb-2">Không tìm thấy trang</h1>
        <p className="text-sm text-muted-foreground mb-6">
          Trang bạn đang tìm không tồn tại hoặc đã được di chuyển.
        </p>
        <Link href="/">
          <Button>
            <Home className="mr-2 h-4 w-4" aria-hidden="true" />
            Về trang chính
          </Button>
        </Link>
      </div>
    </div>
  );
}
