import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Plus } from "lucide-react";
import { DeparturesList } from "@/components/DeparturesList";
import { EmptyState } from "@/components/EmptyState";
import { TripForm } from "@/components/TripForm";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Tabs, TabsList, TabsPanel, TabsTab } from "@/components/ui/Tabs";
import { useFetch } from "@/hooks/useFetch";
import { trips } from "@/lib/api";

type Tab = "created" | "invited";

function ListState({
  isLoading,
  error,
  onRetry,
  empty,
  children,
}: {
  isLoading: boolean;
  error: string | null;
  onRetry: () => void;
  empty: React.ReactNode | null;
  children: React.ReactNode;
}) {
  if (isLoading) return <DeparturesList label="Loading trips" trips={[]} to={() => ""} loading />;
  if (error) {
    return (
      <div
        role="alert"
        className="flex items-center justify-between gap-3 border-t-2 border-danger pt-4 text-sm text-danger"
      >
        <span>{error}</span>
        <Button variant="secondary" size="sm" onClick={onRetry}>
          Retry
        </Button>
      </div>
    );
  }
  return empty ?? children;
}

export default function Dashboard() {
  const [params, setParams] = useSearchParams();
  const tab: Tab = params.get("tab") === "invited" ? "invited" : "created";
  const [creating, setCreating] = useState(false);

  const created = useFetch(() => trips.list(), []);
  const invited = useFetch(() => trips.listInvited(), []);

  return (
    <div>
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-3xl font-semibold tracking-tight">My trips</h1>
        <Button
          onClick={() => {
            setCreating(true);
          }}
        >
          <Plus className="size-4" aria-hidden="true" />
          New trip
        </Button>
      </div>

      <Tabs
        className="mt-6"
        value={tab}
        onValueChange={(v) => {
          setParams({ tab: String(v) }, { replace: true });
        }}
      >
        <TabsList>
          <TabsTab value="created">
            Created <span className="font-mono">({created.data?.length ?? 0})</span>
          </TabsTab>
          <TabsTab value="invited">
            Invited <span className="font-mono">({invited.data?.length ?? 0})</span>
          </TabsTab>
        </TabsList>
        <TabsPanel value="created">
          <ListState
            isLoading={created.isLoading}
            error={created.error}
            onRetry={created.refetch}
            empty={
              created.data?.length === 0 ? (
                <EmptyState
                  title="No trips yet"
                  text="Create a trip, invite your group by email, collect everyone's preferences, then vote on AI-written itineraries."
                />
              ) : null
            }
          >
            <DeparturesList
              label="Created trips"
              trips={created.data ?? []}
              to={(t) => `/dashboard/trip/${t.id.toString()}`}
            />
          </ListState>
        </TabsPanel>
        <TabsPanel value="invited">
          <ListState
            isLoading={invited.isLoading}
            error={invited.error}
            onRetry={invited.refetch}
            empty={
              invited.data?.length === 0 ? (
                <EmptyState
                  title="No invitations yet"
                  text="When someone adds you to a trip, it'll show up here."
                />
              ) : null
            }
          >
            <DeparturesList
              label="Invited trips"
              trips={invited.data ?? []}
              to={(t) => `/trip/${t.participant_token}`}
              linkState={{ from: "dashboard-invited" }}
            />
          </ListState>
        </TabsPanel>
      </Tabs>

      <Dialog open={creating} onOpenChange={setCreating} title="New trip">
        <TripForm
          onCancel={() => {
            setCreating(false);
          }}
          onDone={() => {
            setCreating(false);
            created.refetch();
            invited.refetch();
          }}
        />
      </Dialog>
    </div>
  );
}
