import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Inbox, Plus, Route } from "lucide-react";
import { EmptyState } from "@/components/EmptyState";
import { TripForm } from "@/components/TripForm";
import { TripRow } from "@/components/TripRow";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Skeleton } from "@/components/ui/Skeleton";
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
  if (isLoading) {
    return (
      <div role="status" aria-label="Loading trips" className="divide-y rounded-xl border">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-20 rounded-none" />
        ))}
      </div>
    );
  }
  if (error) {
    return (
      <div
        role="alert"
        className="flex items-center justify-between gap-3 rounded-xl border border-danger/30 bg-danger-subtle px-4 py-3 text-sm text-danger"
      >
        <span>{error}</span>
        <Button variant="secondary" size="sm" onClick={onRetry}>
          Retry
        </Button>
      </div>
    );
  }
  return empty ?? <div className="divide-y overflow-hidden rounded-xl border">{children}</div>;
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
        <h1 className="text-2xl font-semibold tracking-tight">My trips</h1>
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
          <TabsTab value="created">Created ({created.data?.length ?? 0})</TabsTab>
          <TabsTab value="invited">Invited ({invited.data?.length ?? 0})</TabsTab>
        </TabsList>
        <TabsPanel value="created">
          <ListState
            isLoading={created.isLoading}
            error={created.error}
            onRetry={created.refetch}
            empty={
              created.data?.length === 0 ? (
                <EmptyState
                  icon={Route}
                  title="No trips yet"
                  text="Create your first trip and invite your group."
                  action={
                    <Button
                      onClick={() => {
                        setCreating(true);
                      }}
                    >
                      New trip
                    </Button>
                  }
                />
              ) : null
            }
          >
            {created.data?.map((t) => (
              <TripRow key={t.id} trip={t} to={`/dashboard/trip/${t.id.toString()}`} />
            ))}
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
                  icon={Inbox}
                  title="No invitations yet"
                  text="When someone adds you to a trip, it'll show up here."
                />
              ) : null
            }
          >
            {invited.data?.map((t) => (
              <TripRow
                key={t.id}
                trip={t}
                to={`/trip/${t.participant_token}`}
                linkState={{ from: "dashboard-invited" }}
              />
            ))}
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
