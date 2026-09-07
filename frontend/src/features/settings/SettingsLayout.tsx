import { Link } from 'react-router-dom';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/tabs';
import { CompanySettings } from './CompanySettings';
import { BrandingSettings } from './BrandingSettings';
import { NotificationsSettings } from './NotificationsSettings';
import { SecuritySettings } from './SecuritySettings';
import { PaymentProviderSettings } from './PaymentProviderSettings';
import { CustomerSubscriptionSettings } from './CustomerSubscriptionSettings';
import { Button } from '../../components/ui/button';
import {
  Building2,
  Palette,
  Bell,
  Shield,
  CreditCard,
  Wifi,
  Users,
  Server,
  ArrowRight
} from 'lucide-react';

export function SettingsLayout() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">Settings</h1>
        <p className="text-sm text-muted-foreground">
          Manage company preferences, billing gateways, notifications, subscriber access, and security policies.
        </p>
      </div>

      <Tabs defaultValue="company" className="w-full">
        <TabsList className="w-full justify-start border-b border-border bg-transparent p-0 h-auto rounded-none gap-6 flex-wrap">
          <TabsTrigger
            value="company"
            className="flex items-center gap-2 border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent rounded-none px-1 pb-3 pt-2 text-muted-foreground data-[state=active]:text-foreground font-medium"
          >
            <Building2 className="h-4 w-4" />
            Company
          </TabsTrigger>
          <TabsTrigger
            value="payments"
            className="flex items-center gap-2 border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent rounded-none px-1 pb-3 pt-2 text-muted-foreground data-[state=active]:text-foreground font-medium"
          >
            <CreditCard className="h-4 w-4" />
            Payments
          </TabsTrigger>
          <TabsTrigger
            value="branding"
            className="flex items-center gap-2 border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent rounded-none px-1 pb-3 pt-2 text-muted-foreground data-[state=active]:text-foreground font-medium"
          >
            <Palette className="h-4 w-4" />
            Branding
          </TabsTrigger>
          <TabsTrigger
            value="notifications"
            className="flex items-center gap-2 border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent rounded-none px-1 pb-3 pt-2 text-muted-foreground data-[state=active]:text-foreground font-medium"
          >
            <Bell className="h-4 w-4" />
            Notifications
          </TabsTrigger>
          <TabsTrigger
            value="security"
            className="flex items-center gap-2 border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent rounded-none px-1 pb-3 pt-2 text-muted-foreground data-[state=active]:text-foreground font-medium"
          >
            <Shield className="h-4 w-4" />
            Security
          </TabsTrigger>
          <TabsTrigger
            value="subscriptions"
            className="flex items-center gap-2 border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent rounded-none px-1 pb-3 pt-2 text-muted-foreground data-[state=active]:text-foreground font-medium"
          >
            <Users className="h-4 w-4" />
            Subscriptions & OTP
          </TabsTrigger>
          <TabsTrigger
            value="hotspot"
            className="flex items-center gap-2 border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent rounded-none px-1 pb-3 pt-2 text-muted-foreground data-[state=active]:text-foreground font-medium"
          >
            <Wifi className="h-4 w-4 text-blue-500" />
            HotSpots Fleet
          </TabsTrigger>
          <TabsTrigger
            value="uplink"
            className="flex items-center gap-2 border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent rounded-none px-1 pb-3 pt-2 text-muted-foreground data-[state=active]:text-foreground font-medium"
          >
            <Server className="h-4 w-4 text-purple-500" />
            Routers Fleet
          </TabsTrigger>
        </TabsList>

        <TabsContent value="company" className="pt-6">
          <CompanySettings />
        </TabsContent>
        <TabsContent value="payments" className="pt-6">
          <PaymentProviderSettings />
        </TabsContent>
        <TabsContent value="branding" className="pt-6">
          <BrandingSettings />
        </TabsContent>
        <TabsContent value="notifications" className="pt-6">
          <NotificationsSettings />
        </TabsContent>
        <TabsContent value="security" className="pt-6">
          <SecuritySettings />
        </TabsContent>
        <TabsContent value="subscriptions" className="pt-6">
          <CustomerSubscriptionSettings />
        </TabsContent>

        {/* Informational redirects for Hotspots and Routers */}
        <TabsContent value="hotspot" className="pt-6">
          <div className="p-8 max-w-2xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl shadow-sm text-center space-y-4">
            <div className="w-12 h-12 bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 rounded-2xl flex items-center justify-center mx-auto">
              <Wifi className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-gray-900 dark:text-white">
                HotSpots Fleet Workspace
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                HotSpot profiles, captive portals, plan assignments, and anti-tethering are now managed in the dedicated Hotspots workspace.
              </p>
            </div>
            <div>
              <Link to="/hotspots">
                <Button className="bg-blue-600 hover:bg-blue-700 text-white font-medium">
                  Go to Hotspots Fleet <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </Link>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="uplink" className="pt-6">
          <div className="p-8 max-w-2xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl shadow-sm text-center space-y-4">
            <div className="w-12 h-12 bg-purple-50 dark:bg-purple-950/60 text-purple-600 dark:text-purple-400 rounded-2xl flex items-center justify-center mx-auto">
              <Server className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-gray-900 dark:text-white">
                MikroTik Routers Fleet Workspace
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                Router credentials, hardware telemetry, uplink WAN failover, and RADIUS configurations are now managed in the Routers workspace.
              </p>
            </div>
            <div>
              <Link to="/routers">
                <Button className="bg-purple-600 hover:bg-purple-700 text-white font-medium">
                  Go to Routers Fleet <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </Link>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
