import { lazy, Suspense, useEffect } from 'react'
import { Route, Routes, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { Footer, Navbar } from './components/Chrome'
import { ErrorBoundary, Skeleton } from './components/ui'

const Landing = lazy(() => import('./pages/Landing'))
const Lab = lazy(() => import('./pages/Lab'))
const History = lazy(() => import('./pages/History'))
const Guide = lazy(() => import('./pages/Guide'))
const Login = lazy(() => import('./pages/Login'))
const NotFound = lazy(() => import('./pages/NotFound'))

function PageFallback() {
  return (
    <div className="container-x space-y-4 py-16" aria-busy="true" aria-label="Loading">
      <Skeleton className="h-10 w-1/3" /><Skeleton className="h-64 w-full" /><Skeleton className="h-40 w-full" />
    </div>
  )
}

export default function App() {
  const loc = useLocation()
  useEffect(() => { if (!loc.hash) window.scrollTo(0, 0) }, [loc.pathname, loc.hash])
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <main id="main" className="flex-1">
        <ErrorBoundary>
          <Suspense fallback={<PageFallback />}>
            <AnimatePresence mode="wait" initial={false}>
              <motion.div key={loc.pathname} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.25 }}>
                <Routes location={loc}>
                  <Route path="/" element={<Landing />} />
                  <Route path="/lab" element={<Lab />} />
                  <Route path="/history" element={<History />} />
                  <Route path="/guide" element={<Guide />} />
                  <Route path="/login" element={<Login />} />
                  <Route path="*" element={<NotFound />} />
                </Routes>
              </motion.div>
            </AnimatePresence>
          </Suspense>
        </ErrorBoundary>
      </main>
      <Footer />
    </div>
  )
}
