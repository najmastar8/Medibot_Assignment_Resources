import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'MediBot',
  description: 'Role-based clinical assistant for MediAssist',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
