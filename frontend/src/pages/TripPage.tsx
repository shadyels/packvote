import { useParams } from "react-router-dom";

export default function TripPage() {
  const { token } = useParams<{ token: string }>();

  // TODO: implement in participant flow step
  return (
    <main className="min-h-screen bg-background px-4 py-8">
      <p className="text-muted-foreground">Loading trip {token}…</p>
    </main>
  );
}
