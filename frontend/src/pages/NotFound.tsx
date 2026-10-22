import { Link } from 'react-router-dom'
import { LogoMark } from '../components/Logo'

export default function NotFound() {
  return (
    <div className="container-x flex flex-col items-center py-28 text-center">
      <LogoMark size={64} />
      <p className="eyebrow mt-6">Error 404</p>
      <h1 className="h-display mt-3 text-4xl sm:text-5xl">This signal doesn’t exist.</h1>
      <p className="mt-4 max-w-md text-espresso-700">The page you’re looking for flat-lined. Let’s get you back to something with a pulse.</p>
      <div className="mt-8 flex gap-3"><Link to="/" className="btn-primary">Go home</Link><Link to="/lab" className="btn-ghost">Open the Lab</Link></div>
    </div>
  )
}
