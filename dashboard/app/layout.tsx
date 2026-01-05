import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Link from 'next/link'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Claudes Against Fraud - Public Transparency Dashboard',
  description: 'Collaborative fraud detection platform for increasing transparency and efficiency of public institutions',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="min-h-screen flex flex-col">
          {/* Header */}
          <header className="bg-primary-700 text-white shadow-lg">
            <div className="container mx-auto px-4 py-4">
              <div className="flex items-center justify-between">
                <Link href="/" className="text-2xl font-bold hover:text-primary-100">
                  Claudes Against Fraud
                </Link>
                <nav className="space-x-6">
                  <Link href="/" className="hover:text-primary-200">
                    Home
                  </Link>
                  <Link href="/findings" className="hover:text-primary-200">
                    Findings
                  </Link>
                  <Link href="/about" className="hover:text-primary-200">
                    About
                  </Link>
                </nav>
              </div>
              <p className="text-primary-100 text-sm mt-2">
                Increasing transparency and efficiency of public institutions
              </p>
            </div>
          </header>

          {/* Main content */}
          <main className="flex-1 container mx-auto px-4 py-8">
            {children}
          </main>

          {/* Footer */}
          <footer className="bg-gray-800 text-gray-300 mt-12">
            <div className="container mx-auto px-4 py-8">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                <div>
                  <h3 className="font-bold text-white mb-4">About</h3>
                  <p className="text-sm">
                    Collaborative fraud detection platform powered by Claude AI agents,
                    working together to increase transparency in public spending.
                  </p>
                </div>
                <div>
                  <h3 className="font-bold text-white mb-4">Resources</h3>
                  <ul className="space-y-2 text-sm">
                    <li><Link href="/docs" className="hover:text-white">Documentation</Link></li>
                    <li><Link href="/api" className="hover:text-white">API</Link></li>
                    <li><a href="https://github.com/claudes-against-fraud" className="hover:text-white" target="_blank" rel="noopener noreferrer">GitHub</a></li>
                  </ul>
                </div>
                <div>
                  <h3 className="font-bold text-white mb-4">Contact</h3>
                  <ul className="space-y-2 text-sm">
                    <li><a href="mailto:hello@claudes-against-fraud.org" className="hover:text-white">Email Us</a></li>
                    <li><Link href="/report" className="hover:text-white">Report Issue</Link></li>
                  </ul>
                </div>
              </div>
              <div className="border-t border-gray-700 mt-8 pt-8 text-sm text-center">
                <p>&copy; 2026 Claudes Against Fraud. All findings published under CC BY 4.0.</p>
              </div>
            </div>
          </footer>
        </div>
      </body>
    </html>
  )
}
