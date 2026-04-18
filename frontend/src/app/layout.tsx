import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import { Toaster } from "@/components/ui/toast";
import { SkipLink } from "@/components/shared/skip-link";
import { PreferencesEffect } from "@/hooks/use-preferences";
import "./globals.css";

const inter = Inter({ subsets: ["latin", "vietnamese"], display: "swap" });

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://palp.dau.edu.vn";
const SITE_NAME = "PALP - Personalized Adaptive Learning Platform";
const SITE_DESCRIPTION =
  "Nền tảng học tập thích ứng cá nhân hóa cho sinh viên ĐH Kiến trúc Đà Nẵng. Học theo lộ trình BKT, theo dõi tiến độ và nhận hỗ trợ kịp thời từ giảng viên.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: SITE_NAME,
    template: "%s · PALP",
  },
  description: SITE_DESCRIPTION,
  applicationName: "PALP",
  authors: [{ name: "Đại học Kiến trúc Đà Nẵng" }],
  keywords: [
    "EdTech",
    "adaptive learning",
    "BKT",
    "Đà Nẵng",
    "Sức Bền Vật Liệu",
    "personalized learning",
    "Vietnam higher education",
  ],
  creator: "PALP Team",
  publisher: "Đại học Kiến trúc Đà Nẵng",
  formatDetection: { email: false, address: false, telephone: false },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  openGraph: {
    type: "website",
    locale: "vi_VN",
    url: SITE_URL,
    siteName: SITE_NAME,
    title: SITE_NAME,
    description: SITE_DESCRIPTION,
  },
  twitter: {
    card: "summary_large_image",
    title: SITE_NAME,
    description: SITE_DESCRIPTION,
  },
  alternates: {
    canonical: SITE_URL,
  },
  icons: {
    icon: "/favicon.ico",
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#020617" },
  ],
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <body className={inter.className}>
        <PreferencesEffect />
        <SkipLink />
        {children}
        <Toaster />
      </body>
    </html>
  );
}
