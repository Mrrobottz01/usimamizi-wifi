import { RouterProvider } from 'react-router-dom';
import { router } from './router';
import { ThemeProvider } from '../lib/theme-provider';
import { AuthProvider } from '../features/auth/AuthContext';
import { ToastProvider } from '../components/ui/toast';

export function App() {
  return (
    <ThemeProvider defaultTheme="system" storageKey="usimamizi-theme">
      <ToastProvider>
        <AuthProvider>
          <RouterProvider router={router} />
        </AuthProvider>
      </ToastProvider>
    </ThemeProvider>
  );
}
