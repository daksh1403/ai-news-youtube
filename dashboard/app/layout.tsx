import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI News Pipeline — Dashboard",
  description: "Monitor your AI news video pipeline",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
