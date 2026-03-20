import type { Metadata } from "next";
import { Providers } from "@/components/Providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "CutCost — Find the cheapest safe place to buy anything",
  description:
    "CutCost scans merchants worldwide, estimates true total cost including shipping and duties, checks merchant trustworthiness, and recommends the best buying option.",
  openGraph: {
    title: "CutCost",
    description: "Find the cheapest safe place to buy anything.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
