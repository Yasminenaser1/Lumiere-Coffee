import './globals.css'

export const metadata = {
  title: 'Lead IQ — Coffee Shop Pipeline',
  description: 'AI-powered lead scoring for coffee shop sales teams',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
