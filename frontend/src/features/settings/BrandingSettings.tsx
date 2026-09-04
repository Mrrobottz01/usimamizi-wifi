import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../../components/ui/card';
import { Input } from '../../components/ui/input';
import { Button } from '../../components/ui/button';
import { Palette, Image as ImageIcon } from 'lucide-react';

export function BrandingSettings() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center space-x-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Palette className="h-5 w-5" />
            </div>
            <div>
              <CardTitle>Tenant Branding & Captive Portal Design</CardTitle>
              <CardDescription>Customize logo, primary accent colors, and captive portal appearance.</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input label="Brand Accent Color (Hex)" defaultValue="#3B82F6" placeholder="#3B82F6" />
            <Input label="Secondary Accent Color (Hex)" defaultValue="#1E293B" placeholder="#1E293B" />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-medium text-foreground">Company Logo</label>
            <div className="flex items-center space-x-4 rounded-lg border border-dashed border-border p-6 text-center justify-center">
              <ImageIcon className="h-8 w-8 text-muted-foreground" />
              <div className="text-left">
                <p className="text-sm font-medium text-foreground">Upload Logo</p>
                <p className="text-xs text-muted-foreground">PNG, SVG or JPG (max 2MB)</p>
              </div>
              <Button variant="outline" size="sm">Browse File</Button>
            </div>
          </div>
        </CardContent>
        <CardFooter className="justify-end border-t border-border pt-4">
          <Button variant="primary">Save Branding Settings</Button>
        </CardFooter>
      </Card>
    </div>
  );
}
