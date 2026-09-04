import { LucideIcon } from 'lucide-react';
import { EmptyState } from '../../components/ui/empty-state';

interface PlaceholderPageProps {
  title: string;
  description: string;
  phase: string;
  icon: LucideIcon;
}

export function PlaceholderPage({ title, description, phase, icon }: PlaceholderPageProps) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">{title}</h1>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>

      <EmptyState
        icon={icon}
        title={`${title} Module — ${phase}`}
        description="This module is scheduled for implementation in a subsequent phase. Phase 0 foundation establishes software architecture, custom user auth, multi-tenant company isolation, design tokens, and settings."
      />
    </div>
  );
}
