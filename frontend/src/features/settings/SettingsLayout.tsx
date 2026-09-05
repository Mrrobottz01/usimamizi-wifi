import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/tabs';
import { CompanySettings } from './CompanySettings';
import { BrandingSettings } from './BrandingSettings';
import { NotificationsSettings } from './NotificationsSettings';
import { SecuritySettings } from './SecuritySettings';
import { PaymentProviderSettings } from './PaymentProviderSettings';
import { UplinkNetworkSettings } from './UplinkNetworkSettings';
import { HotspotSettingsPage } from './HotspotSettingsPage';
import { Building2, Palette, Bell, Shield, CreditCard, Wifi } from 'lucide-react';

export function SettingsLayout() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">Settings</h1>
        <p className="text-sm text-muted-foreground">Manage your tenant company preferences, branding, payments, notifications, uplink Wi-Fi WAN, and security.</p>
      </div>

      <Tabs defaultValue="payments" className="w-full">
        <TabsList className="w-full justify-start border-b border-border bg-transparent p-0 h-auto rounded-none gap-6">
          <TabsTrigger
            value="payments"
            className="flex items-center gap-2 border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent rounded-none px-1 pb-3 pt-2 text-muted-foreground data-[state=active]:text-foreground font-medium"
          >
            <CreditCard className="h-4 w-4" />
            Payments
          </TabsTrigger>
          <TabsTrigger
            value="uplink"
            className="flex items-center gap-2 border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent rounded-none px-1 pb-3 pt-2 text-muted-foreground data-[state=active]:text-foreground font-medium"
          >
            <Wifi className="h-4 w-4" />
            Uplink WAN
          </TabsTrigger>
          <TabsTrigger
            value="hotspot"
            className="flex items-center gap-2 border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent rounded-none px-1 pb-3 pt-2 text-muted-foreground data-[state=active]:text-foreground font-medium"
          >
            <Shield className="h-4 w-4 text-emerald-500" />
            HotSpot & Protection
          </TabsTrigger>
          <TabsTrigger
            value="company"
            className="flex items-center gap-2 border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent rounded-none px-1 pb-3 pt-2 text-muted-foreground data-[state=active]:text-foreground font-medium"
          >
            <Building2 className="h-4 w-4" />
            Company
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
        </TabsList>

        <TabsContent value="payments" className="pt-6">
          <PaymentProviderSettings />
        </TabsContent>
        <TabsContent value="uplink" className="pt-6">
          <UplinkNetworkSettings />
        </TabsContent>
        <TabsContent value="hotspot" className="pt-6">
          <HotspotSettingsPage />
        </TabsContent>
        <TabsContent value="company" className="pt-6">
          <CompanySettings />
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
      </Tabs>
    </div>
  );
}

