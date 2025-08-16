import type { Metadata } from "next";
import { Inter, Unna } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

const unna = Unna({
  subsets: ["latin"],
  variable: "--font-unna",
  weight: "400",
});

export const metadata: Metadata = {
  title: "SentinelAI - Transforming Chaos into Clarity",
  description:
    "SentinelAI ingests raw 911 incident reports and transforms them into structured, actionable EIDO data—powering the next generation of emergency response.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${unna.variable}`}>
      <body>
        {/* The MainLayout wrapper has been removed to simplify the structure 
            and remove the old header and scrolling text. */}
        {children}
      </body>
    </html>
  );
}
