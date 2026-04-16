import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Toaster } from "@/components/ui/toast";
import { SkipLink } from "@/components/shared/skip-link";
import "./globals.css";

const inter = Inter({ subsets: ["latin", "vietnamese"] });

export const metadata: Metadata = {
  title: "PALP - Personalized Adaptive Learning Platform",
  description: "Nền tảng học tập thích ứng cá nhân hóa - ĐH Kiến trúc Đà Nẵng",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <body className={inter.className}>
        <SkipLink />
        {children}
        <Toaster />
      </body>
    </html>
  );
}
