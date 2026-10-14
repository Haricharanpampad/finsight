import "./globals.css";

export const metadata = {
  title: "FinSight - your business copilot",
  description: "Ask questions about your business finances and get answers, explanations and suggestions.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
