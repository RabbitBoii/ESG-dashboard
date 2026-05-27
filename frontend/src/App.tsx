import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Navbar from './components/Navbar'
import Upload from './pages/Upload'
import Records from './pages/Records'
import RecordDetail from './pages/RecordDetail'
import { Toaster } from 'react-hot-toast'

export default function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-right" toastOptions={{
        style: { background: '#111', color: '#e8e8e8', border: '1px solid #222' }
      }} />
      <div className="min-h-screen bg-[#0a0a0a] text-[#e8e8e8]">
        <Navbar />
        <main className="max-w-[1400px] mx-auto px-6 py-8">
          <Routes>
            <Route path="/" element={<Navigate to="/records" />} />
            <Route path="/upload" element={<Upload />} />
            <Route path="/records" element={<Records />} />
            <Route path="/records/:id" element={<RecordDetail />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}