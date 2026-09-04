import { useAuth } from '../../hooks/useAuth';
import { ThemeToggle } from './ThemeToggle';
import { Dropdown, DropdownItem } from '../ui/dropdown';
import { Building2, LogOut, ChevronDown } from 'lucide-react';
import { Badge } from '../ui/badge';

export function Header() {
  const { user, companies, selectedCompany, setSelectedCompany, logout } = useAuth();

  return (
    <header className="sticky top-0 z-40 flex h-16 w-full items-center justify-between border-b border-border bg-card/95 px-6 backdrop-blur">
      {/* Left: Company Selector Context */}
      <div className="flex items-center space-x-3">
        {companies.length > 0 ? (
          <Dropdown
            trigger={
              <button
                type="button"
                className="flex items-center space-x-2 rounded-lg border border-border bg-background px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-accent focus:outline-none"
              >
                <Building2 className="h-4 w-4 text-primary" />
                <span>{selectedCompany?.name || 'Select Company'}</span>
                <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
              </button>
            }
          >
            {companies.map((c) => (
              <DropdownItem
                key={c.id}
                onClick={() => setSelectedCompany(c)}
                className={selectedCompany?.id === c.id ? 'font-semibold text-primary' : ''}
              >
                <div className="flex items-center justify-between w-full">
                  <span>{c.name}</span>
                  <Badge variant={c.status === 'ACTIVE' ? 'success' : 'secondary'} className="text-[10px] px-1.5 py-0">
                    {c.status}
                  </Badge>
                </div>
              </DropdownItem>
            ))}
          </Dropdown>
        ) : (
          <div className="flex items-center space-x-2 text-sm text-muted-foreground">
            <Building2 className="h-4 w-4" />
            <span>No company assigned</span>
          </div>
        )}
      </div>

      {/* Right: Theme Selector & User Menu */}
      <div className="flex items-center space-x-3">
        <ThemeToggle />

        {user && (
          <Dropdown
            align="right"
            trigger={
              <button
                type="button"
                className="flex items-center space-x-2 rounded-full border border-border bg-background p-1 pr-3 text-sm font-medium text-foreground transition-colors hover:bg-accent focus:outline-none"
              >
                <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-semibold">
                  {user.email[0].toUpperCase()}
                </div>
                <span className="max-w-[120px] truncate hidden sm:inline-block">{user.full_name || user.email}</span>
                <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
              </button>
            }
          >
            <div className="px-3 py-2 border-b border-border text-xs">
              <p className="font-semibold text-foreground truncate">{user.email}</p>
              <p className="text-muted-foreground">{user.is_staff ? 'Staff Admin' : 'Tenant Member'}</p>
            </div>
            <DropdownItem onClick={logout} className="text-destructive hover:bg-destructive/10">
              <LogOut className="mr-2 h-4 w-4" />
              Sign Out
            </DropdownItem>
          </Dropdown>
        )}
      </div>
    </header>
  );
}
