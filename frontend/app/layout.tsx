import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

const sourceHanSans = localFont({
  src: [
    { path: "./fonts/SourceHanSansJP-Regular.otf", weight: "400", style: "normal" },
    { path: "./fonts/SourceHanSansJP-Medium.otf",  weight: "500", style: "normal" },
    { path: "./fonts/SourceHanSansJP-Bold.otf",    weight: "700", style: "normal" },
    { path: "./fonts/SourceHanSansJP-Heavy.otf",   weight: "900", style: "normal" },
  ],
  variable: "--font-source-han",
});

export const metadata: Metadata = {
  title: "はてな展 診断",
  description: "はてな展 診断システム",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja">
      <body className={`${sourceHanSans.variable} antialiased`} style={{ fontFamily: "var(--font-source-han), sans-serif" }}>
        {children}
      </body>
    </html>
  );
}
