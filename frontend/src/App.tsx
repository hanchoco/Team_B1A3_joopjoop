import AppRouter from './router'
import { AppProvider } from './store/AppContext'

export default function App() {
  return (
    <AppProvider>
      <AppRouter />
    </AppProvider>
  )
}
