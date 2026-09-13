import type { Metadata } from 'next';
import '@fontsource-variable/manrope';
import '@fontsource-variable/dm-sans';
import '@fontsource-variable/plus-jakarta-sans';
import './globals.css';
import './form-studio.css';
import './live-workflow.css';
import './journey.css';

export const metadata: Metadata = {
  title: 'Dossier TN — Votre espace de démarches',
  description: 'Préparez vos documents, confirmez les informations et suivez la revue de votre dossier.',
};
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="fr" suppressHydrationWarning>
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
