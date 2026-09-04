import { useTheme } from '../../hooks/useTheme';
import { Sun, Moon, Laptop } from 'lucide-react';
import { Dropdown, DropdownItem } from '../ui/dropdown';

export function ThemeToggle() {
  const { theme, setTheme, resolvedTheme } = useTheme();

  return (
    <Dropdown
      align="right"
      trigger={
        <button
          type="button"
          aria-label="Toggle theme"
          className="flex h-9 w-9 items-center justify-center rounded-md border border-border bg-background text-foreground transition-colors hover:bg-accent hover:text-accent-foreground focus:outline-none focus:ring-2 focus:ring-ring"
        >
          {resolvedTheme === 'dark' ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
        </button>
      }
    >
      <DropdownItem onClick={() => setTheme('light')} className={theme === 'light' ? 'font-semibold text-primary' : ''}>
        <Sun className="mr-2 h-4 w-4" />
        Light
      </DropdownItem>
      <DropdownItem onClick={() => setTheme('dark')} className={theme === 'dark' ? 'font-semibold text-primary' : ''}>
        <Moon className="mr-2 h-4 w-4" />
        Dark
      </DropdownItem>
      <DropdownItem onClick={() => setTheme('system')} className={theme === 'system' ? 'font-semibold text-primary' : ''}>
        <Laptop className="mr-2 h-4 w-4" />
        System
      </DropdownItem>
    </Dropdown>
  );
}
