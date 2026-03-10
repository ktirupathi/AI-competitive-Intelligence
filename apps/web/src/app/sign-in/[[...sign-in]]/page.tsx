import { SignIn } from "@clerk/nextjs";
import { Radar } from "lucide-react";
import Link from "next/link";

export default function SignInPage() {
  return (
    <div className="flex min-h-screen">
      <div className="hidden w-1/2 flex-col justify-between bg-primary/5 p-12 lg:flex">
        <Link href="/" className="flex items-center gap-2">
          <Radar className="h-7 w-7 text-primary" />
          <span className="text-xl font-bold">Scout AI</span>
        </Link>
        <div className="space-y-4">
          <h2 className="text-3xl font-bold">
            Welcome back to your
            <br />
            competitive advantage.
          </h2>
          <p className="text-muted-foreground">
            Sign in to access your competitor intelligence dashboard, review the
            latest briefings, and stay ahead of the market.
          </p>
        </div>
        <p className="text-sm text-muted-foreground">
          &copy; {new Date().getFullYear()} Scout AI
        </p>
      </div>
      <div className="flex flex-1 items-center justify-center p-8">
        <SignIn
          appearance={{
            elements: {
              rootBox: "mx-auto",
              card: "shadow-none",
            },
          }}
        />
      </div>
    </div>
  );
}
