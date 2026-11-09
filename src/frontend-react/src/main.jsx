import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router'
import App from './App.jsx'
import Chat from './routes/Chat.jsx'
import Home from './routes/Home.jsx'
import Newsletter from './routes/Newsletter.jsx'
import Newsletters from './routes/Newsletters.jsx'
import NotFound from './routes/NotFound.jsx'
import Podcasts from './routes/Podcasts.jsx'
import './styles.css'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<App />}>
          <Route index element={<Home />} />
          <Route path="chat" element={<Chat />} />
          <Route path="newsletters" element={<Newsletters />} />
          <Route path="newsletters/:id" element={<Newsletter />} />
          <Route path="podcasts" element={<Podcasts />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
