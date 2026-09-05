import React from 'react';
import { NavLink } from 'react-router-dom';
import { cn } from '../../lib/utils';
import {
  Wifi,
  Settings,
  MessageSquare,
  Key,
  MapPin,
  Router as RouterIcon,
  Radio,
  Activity,
  Users,
  CreditCard,
  Ticket,
  BarChart3,
  DollarSign,
  ShieldCheck,
  Repeat,
} from 'lucide-react';

interface SidebarItemProps {
  to: string;
  icon: React.ElementType;
  label: string;
  badge?: string;
}

function SidebarItem({ to, icon: Icon, label, badge }: SidebarItemProps) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cn(
          'flex items-center justify-between rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
          isActive
            ? 'bg-primary/10 text-primary font-semibold'
            : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
        )
      }
    >
      <div className="flex items-center space-x-3">
        <Icon className="h-4 w-4" />
        <span>{label}</span>
      </div>
      {badge && (
        <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
          {badge}
        </span>
      )}
    </NavLink>
  );
}

export function Sidebar() {
  return (
    <aside className="w-64 shrink-0 border-r border-border bg-card flex flex-col min-h-screen">
      {/* Brand Header */}
      <div className="flex h-16 items-center px-6 border-b border-border">
        <div className="flex items-center space-x-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
            <Wifi className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-base font-bold text-foreground leading-none">Usimamizi</h1>
            <span className="text-[11px] text-muted-foreground font-medium">Wi-Fi Hotspot SaaS</span>
          </div>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 space-y-6 px-4 py-6 overflow-y-auto">
        <div className="space-y-1">
          <p className="px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
            Configuration
          </p>
          <SidebarItem to="/settings" icon={Settings} label="Settings" />
          <SidebarItem to="/notifications/sms-history" icon={MessageSquare} label="SMS Delivery Logs" />
        </div>

        <div className="space-y-1">
          <p className="px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
            Hotspot Management
          </p>
          <SidebarItem to="/locations" icon={MapPin} label="Locations" badge="Phase 3" />
          <SidebarItem to="/routers" icon={RouterIcon} label="Routers" badge="Phase 3" />
          <SidebarItem to="/hotspots" icon={Radio} label="Hotspots" badge="Phase 3" />
          <SidebarItem to="/sessions" icon={Activity} label="Active Sessions" />
          <SidebarItem to="/customers" icon={Users} label="Customers" />
          <SidebarItem to="/subscriptions" icon={Repeat} label="Subscriptions" />
          <SidebarItem to="/plans" icon={CreditCard} label="Internet Plans" />
          <SidebarItem to="/payments" icon={DollarSign} label="Payments & Orders" />
          <SidebarItem to="/walled-garden" icon={ShieldCheck} label="Walled Garden" />
          <SidebarItem to="/vouchers" icon={Ticket} label="Vouchers" />
          <SidebarItem to="/entitlements" icon={Key} label="Access Entitlements" />
          <SidebarItem to="/reports" icon={BarChart3} label="Reports" badge="Phase 8" />
        </div>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-border text-center text-xs text-muted-foreground">
        Usimamizi Wi-Fi v1.0.0 — Phase 0
      </div>
    </aside>
  );
}
