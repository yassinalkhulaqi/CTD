/**
 * The challenge detail drawer: description, notes, timeline and flag form.
 */

import { useCallback, useState } from "react";
import { Flag, MessageSquarePlus, Send } from "lucide-react";
import { formatNumber, formatRelativeTime } from "../../lib/utils";
import { useDashboardStore } from "../../stores/dashboardStore";
import { useNotificationStore } from "../../stores/notificationStore";
import type { Challenge } from "../../types";
import {
  Badge,
  Button,
  Drawer,
  EmptyState,
  Input,
  Skeleton,
  Tabs,
  TabsContent,
  Textarea,
  useToast,
} from "../../components/ui";
import {
  useAddNote,
  useChallengeNotes,
  useChallengeTimeline,
  useSubmitFlag,
} from "./hooks";
import styles from "./ChallengeDrawer.module.css";

/** Props accepted by {@link ChallengeDrawer}. */
export interface ChallengeDrawerProps {
  /** The challenge being inspected. */
  challenge: Challenge | null;
  /** Called when the drawer requests to be closed. */
  onClose: () => void;
}

/**
 * Render the challenge detail drawer.
 *
 * @param props - The component props.
 * @returns The drawer element.
 */
export function ChallengeDrawer({ challenge, onClose }: ChallengeDrawerProps) {
  const [tab, setTab] = useState("details");
  const [flag, setFlag] = useState("");
  const [note, setNote] = useState("");

  const members = useDashboardStore((state) => state.members);
  const notify = useNotificationStore((state) => state.push);
  const toast = useToast();

  const notes = useChallengeNotes(challenge?.id ?? null);
  const timeline = useChallengeTimeline(challenge?.id ?? null);
  const submitFlag = useSubmitFlag();
  const addNote = useAddNote(challenge?.id ?? null);

  const author = members[0];

  const handleSubmitFlag = useCallback(async () => {
    if (!challenge || !author) return;
    const result = await submitFlag.mutate({
      challengeId: challenge.id,
      memberId: author.id,
      flag,
    });
    if (result?.accepted) {
      notify({
        tone: "success",
        title: "Solve recorded",
        description: result.message,
      });
      toast.push(result.message, { tone: "success" });
      setFlag("");
    } else {
      notify({
        tone: "error",
        title: "Flag rejected",
        description: result?.message,
      });
      toast.push(result?.message ?? "The flag was rejected", { tone: "error" });
    }
  }, [author, challenge, flag, notify, submitFlag, toast]);

  const handleAddNote = useCallback(async () => {
    if (!challenge || !author || !note.trim()) return;
    const created = await addNote.mutate({
      memberId: author.id,
      body: note,
    });
    if (created) {
      setNote("");
      toast.push("Note saved", { tone: "success" });
    }
  }, [addNote, author, challenge, note, toast]);

  return (
    <Drawer
      open={challenge !== null}
      onClose={onClose}
      title={challenge?.title ?? "Challenge"}
      width={520}
      footer={
        challenge ? (
          <div className={styles.footer}>
            <span className={styles.footerMeta}>
              {formatNumber(challenge.points)} points · {challenge.category} ·{" "}
              {challenge.difficulty}
            </span>
          </div>
        ) : null
      }
    >
      {challenge ? (
        <Tabs value={tab} onValueChange={setTab} label="Challenge details">
          <TabsContent value="details" className={styles.tabPanel}>
            <p className={styles.description}>
              {challenge.description ||
                "No description has been published for this challenge."}
            </p>

            <div className={styles.metaGrid}>
              <div>
                <span className={styles.metaLabel}>Status</span>
                <Badge
                  tone={challenge.status === "solved" ? "success" : "accent"}
                  dot
                >
                  {challenge.status}
                </Badge>
              </div>
              <div>
                <span className={styles.metaLabel}>Difficulty</span>
                <span className={styles.metaValue}>{challenge.difficulty}</span>
              </div>
              <div>
                <span className={styles.metaLabel}>Category</span>
                <span className={styles.metaValue}>{challenge.category}</span>
              </div>
              <div>
                <span className={styles.metaLabel}>Time left</span>
                <span className={styles.metaValue}>
                  {Math.max(0, Math.round(challenge.seconds_remaining / 60))}{" "}
                  minutes
                </span>
              </div>
            </div>

            {challenge.tags.length > 0 ? (
              <div className={styles.tags}>
                {challenge.tags.map((tag) => (
                  <Badge key={tag} tone="info">
                    {tag}
                  </Badge>
                ))}
              </div>
            ) : null}

            <div className={styles.flagBlock}>
              <h3 className={styles.sectionTitle}>
                <Flag size={14} aria-hidden="true" />
                Submit a flag
              </h3>
              <Input
                value={flag}
                onChange={(event) => setFlag(event.target.value)}
                placeholder="flag{...}"
                hideLabel
                aria-label="Flag"
                onKeyDown={(event) => {
                  if (event.key === "Enter") void handleSubmitFlag();
                }}
              />
              <Button
                icon={<Send size={14} />}
                loading={submitFlag.isPending}
                disabled={!flag.trim() || !author}
                onClick={() => void handleSubmitFlag()}
                className={styles.flagSubmit}
              >
                Submit flag
              </Button>
              {!author ? (
                <p className={styles.hint}>
                  Add a team member before recording a solve.
                </p>
              ) : null}
            </div>
          </TabsContent>

          <TabsContent value="notes" className={styles.tabPanel}>
            <div className={styles.noteComposer}>
              <Textarea
                value={note}
                onChange={(event) => setNote(event.target.value)}
                placeholder="Share what you found with the rest of the team…"
                maxLength={4000}
                showCount
                hideLabel
                aria-label="Note"
              />
              <Button
                variant="secondary"
                icon={<MessageSquarePlus size={14} />}
                loading={addNote.isPending}
                disabled={!note.trim() || !author}
                onClick={() => void handleAddNote()}
              >
                Add note
              </Button>
            </div>

            {notes.isLoading ? (
              <Skeleton height={60} />
            ) : (notes.data?.length ?? 0) === 0 ? (
              <EmptyState
                icon={<MessageSquarePlus size={20} />}
                title="No notes yet"
                description="Document your findings so the team can pick up where you left off."
              />
            ) : (
              <ul className={styles.notes}>
                {notes.data?.map((item) => (
                  <li key={item.id} className={styles.note}>
                    <div className={styles.noteHead}>
                      <span className={styles.noteAuthor}>
                        {members.find((member) => member.id === item.member_id)
                          ?.display_name ?? "Anonymous"}
                      </span>
                      <time
                        className={styles.noteTime}
                        dateTime={item.created_at}
                      >
                        {formatRelativeTime(item.created_at)}
                      </time>
                    </div>
                    <p className={styles.noteBody}>{item.body}</p>
                  </li>
                ))}
              </ul>
            )}
          </TabsContent>

          <TabsContent value="timeline" className={styles.tabPanel}>
            {timeline.isLoading ? (
              <Skeleton height={60} />
            ) : (timeline.data?.length ?? 0) === 0 ? (
              <EmptyState
                icon={<Flag size={20} />}
                title="No solve recorded"
                description="The timeline shows every flag submitted for this challenge."
              />
            ) : (
              <ol className={styles.timeline}>
                {timeline.data?.map((entry) => (
                  <li key={entry.solve_id} className={styles.timelineEntry}>
                    <span className={styles.timelineDot} aria-hidden="true" />
                    <div className={styles.timelineBody}>
                      <p className={styles.timelineTitle}>
                        <strong>@{entry.member_handle}</strong> solved the
                        challenge
                      </p>
                      <p className={styles.timelineMeta}>
                        {formatRelativeTime(entry.solved_at)} ·{" "}
                        {formatNumber(entry.points_awarded)} points
                        {entry.masked_flag ? ` · ${entry.masked_flag}` : ""}
                      </p>
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </TabsContent>
        </Tabs>
      ) : null}
    </Drawer>
  );
}
