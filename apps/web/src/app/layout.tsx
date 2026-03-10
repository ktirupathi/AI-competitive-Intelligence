import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "Scout AI - AI Competitive Intelligence Agent",
  description:
    "Monitor competitors automatically. Get AI-powered weekly briefings with actionable insights. Stay ahead of your competition.",
  keywords: [
    "competitive intelligence",
    "AI",
    "competitor monitoring",
    "market analysis",
    "business intelligence",
  ],
  openGraph: {
    title: "Scout AI - AI Competitive Intelligence Agent",
    description:
      "Monitor competitors automatically. Get AI-powered weekly briefings with actionable insights.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ClerkProvider>
      <html lang="en" className="dark">
        <body className={`${inter.variable} font-sans antialiased`}>
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}
