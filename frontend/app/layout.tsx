import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Autonomous Financial Advisor",
  description: "Financial advisor chat agent over supplied market and portfolio data"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
