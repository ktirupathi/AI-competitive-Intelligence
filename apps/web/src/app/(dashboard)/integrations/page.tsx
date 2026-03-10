"use client";

import { useState } from "react";
import {
  Slack,
  Mail,
  Webhook,
  CheckCircle2,
  XCircle,
  Settings,
  ExternalLink,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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
import { getStatusColor } from "@/lib/utils";

export default function IntegrationsPage() {
  const [slackConnected, setSlackConnected] = useState(true);
  const [slackChannel, setSlackChannel] = useState("#competitive-intel");
  const [emailEnabled, setEmailEnabled] = useState(true);
  const [emailAddress, setEmailAddress] = useState("team@company.com");
  const [webhookEnabled, setWebhookEnabled] = useState(false);
  const [webhookUrl, setWebhookUrl] = useState("");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Integrations</h1>
        <p className="text-muted-foreground">
          Connect Scout AI with your favorite tools to receive briefings and
          alerts
        </p>
      </div>

      <div className="grid gap-6">
        {/* Slack Integration */}
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-[#4A154B]/10">
                  <Slack className="h-6 w-6 text-[#4A154B]" />
                </div>
                <div>
                  <CardTitle className="text-lg">Slack</CardTitle>
                  <CardDescription>
                    Receive briefings and real-time alerts in Slack
                  </CardDescription>
                </div>
              </div>
              <Badge
                variant="outline"
                className={getStatusColor(
                  slackConnected ? "connected" : "disconnected"
                )}
              >
                {slackConnected ? (
                  <CheckCircle2 className="mr-1 h-3 w-3" />
                ) : (
                  <XCircle className="mr-1 h-3 w-3" />
                )}
                {slackConnected ? "Connected" : "Disconnected"}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {slackConnected ? (
              <>
                <div className="grid gap-2">
                  <Label>Delivery Channel</Label>
                  <Select value={slackChannel} onValueChange={setSlackChannel}>
                    <SelectTrigger className="max-w-sm">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="#competitive-intel">
                        #competitive-intel
                      </SelectItem>
                      <SelectItem value="#strategy">#strategy</SelectItem>
                      <SelectItem value="#general">#general</SelectItem>
                      <SelectItem value="#product">#product</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    Weekly briefings and critical alerts will be posted to this
                    channel
                  </p>
                </div>
                <Separator />
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">Weekly Briefings</p>
                    <p className="text-xs text-muted-foreground">
                      Post full briefing to Slack every Monday
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">Critical Alerts</p>
                    <p className="text-xs text-muted-foreground">
                      Instant notification for critical impact changes
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>
                <Separator />
                <div className="flex gap-2">
                  <Button variant="outline" size="sm">
                    <Settings className="mr-2 h-3.5 w-3.5" />
                    Configure
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-destructive hover:text-destructive"
                    onClick={() => setSlackConnected(false)}
                  >
                    Disconnect
                  </Button>
                </div>
              </>
            ) : (
              <Button onClick={() => setSlackConnected(true)}>
                <Slack className="mr-2 h-4 w-4" />
                Connect to Slack
              </Button>
            )}
          </CardContent>
        </Card>

        {/* Email Integration */}
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-blue-500/10">
                  <Mail className="h-6 w-6 text-blue-500" />
                </div>
                <div>
                  <CardTitle className="text-lg">Email</CardTitle>
                  <CardDescription>
                    Get briefings and alerts delivered to your inbox
                  </CardDescription>
                </div>
              </div>
              <Badge
                variant="outline"
                className={getStatusColor(
                  emailEnabled ? "connected" : "disconnected"
                )}
              >
                {emailEnabled ? (
                  <CheckCircle2 className="mr-1 h-3 w-3" />
                ) : (
                  <XCircle className="mr-1 h-3 w-3" />
                )}
                {emailEnabled ? "Enabled" : "Disabled"}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-2">
              <Label>Email Address</Label>
              <div className="flex gap-2 max-w-sm">
                <Input
                  value={emailAddress}
                  onChange={(e) => setEmailAddress(e.target.value)}
                  placeholder="you@company.com"
                />
                <Button variant="outline" size="sm">
                  Update
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Additional recipients can be added in Settings
              </p>
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">Weekly Briefings</p>
                <p className="text-xs text-muted-foreground">
                  Receive full briefing via email every Monday
                </p>
              </div>
              <Switch
                checked={emailEnabled}
                onCheckedChange={setEmailEnabled}
              />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">Critical Alerts</p>
                <p className="text-xs text-muted-foreground">
                  Immediate email for critical changes
                </p>
              </div>
              <Switch defaultChecked />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">Daily Digest</p>
                <p className="text-xs text-muted-foreground">
                  Summary of all changes detected each day
                </p>
              </div>
              <Switch />
            </div>
          </CardContent>
        </Card>

        {/* Webhook Integration */}
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-orange-500/10">
                  <Webhook className="h-6 w-6 text-orange-500" />
                </div>
                <div>
                  <CardTitle className="text-lg">Webhooks</CardTitle>
                  <CardDescription>
                    Send events to your own systems via HTTP webhooks
                  </CardDescription>
                </div>
              </div>
              <Badge
                variant="outline"
                className={getStatusColor(
                  webhookEnabled ? "connected" : "disconnected"
                )}
              >
                {webhookEnabled ? (
                  <CheckCircle2 className="mr-1 h-3 w-3" />
                ) : (
                  <XCircle className="mr-1 h-3 w-3" />
                )}
                {webhookEnabled ? "Active" : "Inactive"}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-2">
              <Label>Webhook URL</Label>
              <div className="flex gap-2 max-w-lg">
                <Input
                  value={webhookUrl}
                  onChange={(e) => setWebhookUrl(e.target.value)}
                  placeholder="https://your-api.com/webhooks/scout-ai"
                />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setWebhookEnabled(!!webhookUrl)}
                >
                  {webhookEnabled ? "Update" : "Activate"}
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                We will send POST requests with JSON payloads to this URL
              </p>
            </div>
            {webhookEnabled && (
              <>
                <Separator />
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">Briefing Events</p>
                    <p className="text-xs text-muted-foreground">
                      Triggered when a new briefing is generated
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">Change Events</p>
                    <p className="text-xs text-muted-foreground">
                      Triggered when a competitor change is detected
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">Alert Events</p>
                    <p className="text-xs text-muted-foreground">
                      Triggered for critical and high-impact changes
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>
                <Separator />
                <div className="rounded-lg bg-muted/50 p-3">
                  <p className="text-xs font-medium mb-1">
                    Last delivery status
                  </p>
                  <p className="text-xs text-muted-foreground">
                    200 OK - 2 hours ago
                  </p>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
