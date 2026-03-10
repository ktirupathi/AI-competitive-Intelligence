"use client";

import { useState } from "react";
import {
  User,
  Clock,
  Bell,
  CreditCard,
  ExternalLink,
  Save,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { createBillingPortalSession } from "@/lib/api";

export default function SettingsPage() {
  const [firstName, setFirstName] = useState("Alex");
  const [lastName, setLastName] = useState("Johnson");
  const [email] = useState("alex@company.com");

  const [deliveryDay, setDeliveryDay] = useState("monday");
  const [deliveryTime, setDeliveryTime] = useState("08:00");
  const [timezone, setTimezone] = useState("America/New_York");

  const [emailBriefings, setEmailBriefings] = useState(true);
  const [emailAlerts, setEmailAlerts] = useState(true);
  const [slackBriefings, setSlackBriefings] = useState(true);
  const [slackAlerts, setSlackAlerts] = useState(true);
  const [criticalOnly, setCriticalOnly] = useState(false);

  const handleManageBilling = async () => {
    try {
      const { url } = await createBillingPortalSession();
      window.location.href = url;
    } catch {
      // In demo mode, just show alert
      alert("Billing portal would open here in production.");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-muted-foreground">
          Manage your account and preferences
        </p>
      </div>

      <div className="grid gap-6 max-w-3xl">
        {/* Profile */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <User className="h-5 w-5 text-primary" />
              <CardTitle className="text-lg">Profile</CardTitle>
            </div>
            <CardDescription>
              Manage your personal information
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="grid gap-2">
                <Label htmlFor="firstName">First Name</Label>
                <Input
                  id="firstName"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="lastName">Last Name</Label>
                <Input
                  id="lastName"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                />
              </div>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" value={email} disabled />
              <p className="text-xs text-muted-foreground">
                Email is managed through your authentication provider
              </p>
            </div>
            <Button size="sm" className="gap-2">
              <Save className="h-3.5 w-3.5" />
              Save Changes
            </Button>
          </CardContent>
        </Card>

        {/* Delivery Preferences */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Clock className="h-5 w-5 text-primary" />
              <CardTitle className="text-lg">Delivery Preferences</CardTitle>
            </div>
            <CardDescription>
              Configure when you receive your weekly briefings
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="grid gap-2">
                <Label>Briefing Day</Label>
                <Select value={deliveryDay} onValueChange={setDeliveryDay}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="monday">Monday</SelectItem>
                    <SelectItem value="tuesday">Tuesday</SelectItem>
                    <SelectItem value="wednesday">Wednesday</SelectItem>
                    <SelectItem value="thursday">Thursday</SelectItem>
                    <SelectItem value="friday">Friday</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-2">
                <Label>Delivery Time</Label>
                <Select value={deliveryTime} onValueChange={setDeliveryTime}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="06:00">6:00 AM</SelectItem>
                    <SelectItem value="07:00">7:00 AM</SelectItem>
                    <SelectItem value="08:00">8:00 AM</SelectItem>
                    <SelectItem value="09:00">9:00 AM</SelectItem>
                    <SelectItem value="10:00">10:00 AM</SelectItem>
                    <SelectItem value="12:00">12:00 PM</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-2">
                <Label>Timezone</Label>
                <Select value={timezone} onValueChange={setTimezone}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="America/New_York">
                      Eastern (ET)
                    </SelectItem>
                    <SelectItem value="America/Chicago">
                      Central (CT)
                    </SelectItem>
                    <SelectItem value="America/Denver">
                      Mountain (MT)
                    </SelectItem>
                    <SelectItem value="America/Los_Angeles">
                      Pacific (PT)
                    </SelectItem>
                    <SelectItem value="Europe/London">GMT/BST</SelectItem>
                    <SelectItem value="Europe/Berlin">CET/CEST</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              Your next briefing will be delivered on{" "}
              {deliveryDay.charAt(0).toUpperCase() + deliveryDay.slice(1)} at{" "}
              {deliveryTime === "08:00" ? "8:00 AM" : deliveryTime}{" "}
              {timezone === "America/New_York" ? "ET" : timezone}
            </p>
            <Button size="sm" className="gap-2">
              <Save className="h-3.5 w-3.5" />
              Save Preferences
            </Button>
          </CardContent>
        </Card>

        {/* Notification Preferences */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Bell className="h-5 w-5 text-primary" />
              <CardTitle className="text-lg">
                Notification Preferences
              </CardTitle>
            </div>
            <CardDescription>
              Choose how and when you want to be notified
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-4">
              <h4 className="text-sm font-medium">Email Notifications</h4>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm">Weekly Briefings</p>
                  <p className="text-xs text-muted-foreground">
                    Receive the full weekly briefing via email
                  </p>
                </div>
                <Switch
                  checked={emailBriefings}
                  onCheckedChange={setEmailBriefings}
                />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm">Real-time Alerts</p>
                  <p className="text-xs text-muted-foreground">
                    Get instant email alerts for significant changes
                  </p>
                </div>
                <Switch
                  checked={emailAlerts}
                  onCheckedChange={setEmailAlerts}
                />
              </div>
            </div>

            <Separator />

            <div className="space-y-4">
              <h4 className="text-sm font-medium">Slack Notifications</h4>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm">Weekly Briefings</p>
                  <p className="text-xs text-muted-foreground">
                    Post briefing summary to Slack
                  </p>
                </div>
                <Switch
                  checked={slackBriefings}
                  onCheckedChange={setSlackBriefings}
                />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm">Real-time Alerts</p>
                  <p className="text-xs text-muted-foreground">
                    Send instant Slack alerts for significant changes
                  </p>
                </div>
                <Switch
                  checked={slackAlerts}
                  onCheckedChange={setSlackAlerts}
                />
              </div>
            </div>

            <Separator />

            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">Critical Alerts Only</p>
                <p className="text-xs text-muted-foreground">
                  Only receive notifications for critical-impact changes
                </p>
              </div>
              <Switch
                checked={criticalOnly}
                onCheckedChange={setCriticalOnly}
              />
            </div>

            <Button size="sm" className="gap-2">
              <Save className="h-3.5 w-3.5" />
              Save Notifications
            </Button>
          </CardContent>
        </Card>

        {/* Billing */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <CreditCard className="h-5 w-5 text-primary" />
              <CardTitle className="text-lg">Billing</CardTitle>
            </div>
            <CardDescription>
              Manage your subscription and billing details
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between rounded-lg border p-4">
              <div>
                <div className="flex items-center gap-2">
                  <h4 className="font-semibold">Professional Plan</h4>
                  <Badge>Current</Badge>
                </div>
                <p className="mt-1 text-sm text-muted-foreground">
                  $149/month - Up to 10 competitors
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  7 of 10 competitor slots used
                </p>
              </div>
              <Button variant="outline" size="sm">
                Upgrade to Enterprise
              </Button>
            </div>

            <div className="flex items-center justify-between rounded-lg border p-4">
              <div>
                <h4 className="text-sm font-medium">Next billing date</h4>
                <p className="text-sm text-muted-foreground">
                  April 1, 2026 - $149.00
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                className="gap-2"
                onClick={handleManageBilling}
              >
                Manage Billing
                <ExternalLink className="h-3.5 w-3.5" />
              </Button>
            </div>

            <p className="text-xs text-muted-foreground">
              Billing is managed through Stripe. Click &quot;Manage
              Billing&quot; to update your payment method, view invoices, or
              cancel your subscription.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
