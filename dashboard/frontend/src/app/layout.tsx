import type { Metadata } from 'next';
import { QueryProvider } from './providers';
import '@/styles/globals.css';

export const metadata: Metadata = {
  title: 'Amazon PPC AI Dashboard',
  description: 'AI-powered PPC management dashboard for Amazon Vendor Central',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <QueryProvider>
          {children}
        </QueryProvider>
      </body>
    </html>
  );
}

