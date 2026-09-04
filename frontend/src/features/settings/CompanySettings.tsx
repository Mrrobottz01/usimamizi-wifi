import { useAuth } from '../../hooks/useAuth';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../../components/ui/card';
import { Input } from '../../components/ui/input';
import { Select } from '../../components/ui/select';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { EmptyState } from '../../components/ui/empty-state';
import { Building2 } from 'lucide-react';

export function CompanySettings() {
  const { selectedCompany } = useAuth();

  if (!selectedCompany) {
    return (
      <EmptyState
        icon={Building2}
        title="No Company Selected"
        description="Select or create a company to manage company profile settings."
      />
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Company Profile</CardTitle>
              <CardDescription>Manage business information and operational defaults.</CardDescription>
            </div>
            <Badge variant={selectedCompany.status === 'ACTIVE' ? 'success' : 'secondary'}>
              {selectedCompany.status}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input label="Company Name" defaultValue={selectedCompany.name} />
            <Input label="URL Slug" defaultValue={selectedCompany.slug} disabled />
            <Input label="Legal Name" defaultValue={selectedCompany.legal_name || ''} placeholder="Company Legal Name LLC" />
            <Input label="Support Phone" defaultValue={selectedCompany.phone || ''} placeholder="+255 700 000 000" />
            <Input label="Support Email" defaultValue={selectedCompany.email || ''} placeholder="support@company.com" />
            <Select label="Country" defaultValue={selectedCompany.country}>
              <option value="TZ">Tanzania (TZ)</option>
              <option value="KE">Kenya (KE)</option>
              <option value="UG">Uganda (UG)</option>
              <option value="RW">Rwanda (RW)</option>
            </Select>
            <Select label="Default Currency" defaultValue={selectedCompany.currency}>
              <option value="TZS">TZS (Tanzanian Shilling)</option>
              <option value="KES">KES (Kenyan Shilling)</option>
              <option value="UGX">UGX (Ugandan Shilling)</option>
              <option value="USD">USD (US Dollar)</option>
            </Select>
            <Select label="Timezone" defaultValue={selectedCompany.timezone}>
              <option value="Africa/Dar_es_Salaam">Africa/Dar_es_Salaam (EAT)</option>
              <option value="Africa/Nairobi">Africa/Nairobi (EAT)</option>
              <option value="Africa/Kampala">Africa/Kampala (EAT)</option>
            </Select>
          </div>
        </CardContent>
        <CardFooter className="justify-end border-t border-border pt-4">
          <Button variant="primary">Save Company Profile</Button>
        </CardFooter>
      </Card>
    </div>
  );
}
