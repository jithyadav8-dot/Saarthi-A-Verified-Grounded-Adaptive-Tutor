import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Saarthi — A Verified-Grounded Adaptive Tutor",
  description: "AI study companion grounded in course videos, textbooks & slides with Bayesian Knowledge Tracing & Dual-LLM verified assessment.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className="h-full antialiased"
    >
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              try {
                var theme = localStorage.getItem('saarthi-theme');
                if (theme === 'dark' || (!theme && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
                  document.documentElement.classList.add('dark');
                } else {
                  document.documentElement.classList.remove('dark');
                }
              } catch (_) {}
            `,
          }}
        />
      </head>
      <body suppressHydrationWarning className="min-h-full flex flex-col bg-[#fafafa] dark:bg-[#06090e] text-zinc-900 dark:text-[#f3f4f6] transition-colors">
        {children}
      </body>
    </html>
  );
}
