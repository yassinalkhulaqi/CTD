/**
 * A living gallery of the dashboard design system.
 *
 * The gallery doubles as visual documentation and as a smoke test that every
 * primitive renders without runtime errors.
 */

import { useState } from "react";
import {
  Activity,
  Bell,
  Flag,
  Search,
  ShieldCheck,
  Trophy,
  Users,
  Zap,
} from "lucide-react";
import {
  Avatar,
  AvatarGroup,
  Badge,
  Button,
  ButtonGroup,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Checkbox,
  Divider,
  Drawer,
  EmptyState,
  ErrorState,
  IconButton,
  Input,
  Kbd,
  Menu,
  MenuDivider,
  MenuItem,
  Modal,
  Progress,
  ScoreRing,
  Select,
  Skeleton,
  Spinner,
  StatCard,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  Textarea,
  ThemeToggle,
  Tooltip,
} from "./ui";
import styles from "./ComponentShowcase.module.css";

const TEAM_MEMBERS = [
  { name: "Nyx Chandler", presence: "online" as const },
  { name: "Kestrel Vane", presence: "away" as const },
  { name: "Bitrot", presence: "offline" as const },
  { name: "Saffron Ilves", presence: "online" as const },
  { name: "Cortex", presence: "offline" as const },
];

/**
 * Render the design system gallery.
 *
 * @returns The gallery element.
 */
export function ComponentShowcase() {
  const [tab, setTab] = useState("buttons");
  const [modalOpen, setModalOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [checked, setChecked] = useState(true);
  const [toggled, setToggled] = useState(false);

  return (
    <div className={styles.showcase}>
      <header className={styles.showcaseHeader}>
        <div>
          <h1 className={styles.showcaseTitle}>Design system</h1>
          <p className={styles.showcaseSubtitle}>
            Every primitive used by the CTF Team Dashboard, rendered with live data.
          </p>
        </div>
        <ThemeToggle />
      </header>

      <div className={styles.statGrid}>
        <StatCard
          label="Teams"
          value={4}
          icon={<ShieldCheck size={16} />}
          accent="#6366f1"
          trend={{ value: "+1 today", direction: "up" }}
          meta="of 8 registered"
        />
        <StatCard
          label="Solves"
          value={128}
          icon={<Flag size={16} />}
          accent="#22d3ee"
          trend={{ value: "+12 / h", direction: "up" }}
          meta="across all categories"
        />
        <StatCard
          label="Members online"
          value={9}
          icon={<Users size={16} />}
          accent="#34d399"
          trend={{ value: "steady", direction: "flat" }}
          meta="of 16 members"
        />
        <StatCard
          label="Points"
          value="12.4k"
          icon={<Trophy size={16} />}
          accent="#f59e0b"
          loading={false}
          trend={{ value: "-3%", direction: "down" }}
          meta="vs last hour"
        />
      </div>

      <Card>
        <Tabs value={tab} onValueChange={setTab}>
          <CardHeader
            actions={
              <ButtonGroup>
                <Button variant="secondary" size="sm" icon={<Search size={14} />}>
                  Search
                </Button>
                <Button size="sm" icon={<Zap size={14} />}>
                  Record solve
                </Button>
              </ButtonGroup>
            }
          >
            <CardTitle>Component gallery</CardTitle>
          </CardHeader>

          <CardContent>
            <TabsList>
              <TabsTrigger value="buttons">Buttons</TabsTrigger>
              <TabsTrigger value="forms">Forms</TabsTrigger>
              <TabsTrigger value="data">Data</TabsTrigger>
              <TabsTrigger value="feedback">Feedback</TabsTrigger>
              <TabsTrigger value="overlays">Overlays</TabsTrigger>
            </TabsList>

            <TabsContent value="buttons" className={styles.panel}>
              <div className={styles.row}>
                <Button variant="primary">Primary</Button>
                <Button variant="secondary">Secondary</Button>
                <Button variant="ghost">Ghost</Button>
                <Button variant="subtle">Subtle</Button>
                <Button variant="danger">Danger</Button>
              </div>
              <div className={styles.row}>
                <Button size="sm">Small</Button>
                <Button size="md">Medium</Button>
                <Button size="lg">Large</Button>
                <Button loading loadingLabel="Saving…">
                  Loading
                </Button>
                <Button disabled>Disabled</Button>
              </div>
              <div className={styles.row}>
                <IconButton icon={<Bell size={16} />} label="Notifications" />
                <IconButton icon={<Activity size={16} />} label="Activity" variant="secondary" />
                <Tooltip content="Tooltips appear after a short delay">
                  <Button variant="secondary">Hover me</Button>
                </Tooltip>
              </div>
            </TabsContent>

            <TabsContent value="forms" className={styles.panel}>
              <div className={styles.formGrid}>
                <Input label="Handle" placeholder="nyx" hint="Lowercase, 2 to 32 characters" />
                <Input label="Flag" placeholder="flag{...}" error="Flag format looks wrong" />
                <Select
                  label="Category"
                  options={[
                    { value: "web", label: "Web" },
                    { value: "crypto", label: "Crypto" },
                    { value: "pwn", label: "Binary" },
                  ]}
                />
                <Textarea label="Notes" maxLength={200} showCount defaultValue="Reverse the packer first." />
              </div>
              <Divider />
              <div className={styles.row}>
                <Checkbox checked={checked} onChange={(event) => setChecked(event.target.checked)}>
                  Send a heartbeat
                </Checkbox>
                <Switch checked={toggled} onChange={(event) => setToggled(event.target.checked)}>
                  Auto refresh
                </Switch>
              </div>
            </TabsContent>

            <TabsContent value="data" className={styles.panel}>
              <div className={styles.row}>
                <Badge tone="accent" dot>
                  Active
                </Badge>
                <Badge tone="success">Solved</Badge>
                <Badge tone="warning" outline>
                  Locked
                </Badge>
                <Badge tone="danger" pulse>
                  Overdue
                </Badge>
                <Kbd>⌘</Kbd>
                <Kbd>K</Kbd>
              </div>
              <div className={styles.row}>
                <AvatarGroup>
                  {TEAM_MEMBERS.map((member) => (
                    <Avatar key={member.name} name={member.name} presence={member.presence} size="sm" />
                  ))}
                </AvatarGroup>
                <ScoreRing value={0.68} size={56} />
                <Progress value={0.42} label="Overall completion" />
              </div>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableHeaderCell>Member</TableHeaderCell>
                    <TableHeaderCell align="right">Solves</TableHeaderCell>
                    <TableHeaderCell align="right">Points</TableHeaderCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {TEAM_MEMBERS.slice(0, 4).map((member, index) => (
                    <TableRow key={member.name} selected={index === 0}>
                      <TableCell>
                        <span className={styles.memberCell}>
                          <Avatar name={member.name} size="sm" />
                          {member.name}
                        </span>
                      </TableCell>
                      <TableCell align="right">{12 - index * 2}</TableCell>
                      <TableCell align="right">{1840 - index * 310}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TabsContent>

            <TabsContent value="feedback" className={styles.panel}>
              <div className={styles.row}>
                <Skeleton width={120} height={14} />
                <Skeleton width={200} height={14} />
                <Spinner />
              </div>
              <EmptyState
                icon={<Flag size={22} />}
                title="No solves recorded yet"
                description="Record the first flag to start the timeline."
                action={<Button size="sm">Record solve</Button>}
              />
              <ErrorState
                message="The realtime gateway did not respond within 5 seconds."
                onRetry={() => undefined}
              />
            </TabsContent>

            <TabsContent value="overlays" className={styles.panel}>
              <div className={styles.row}>
                <Button onClick={() => setModalOpen(true)}>Open modal</Button>
                <Button variant="secondary" onClick={() => setDrawerOpen(true)}>
                  Open drawer
                </Button>
                <div className={styles.menuAnchor}>
                  <Button variant="ghost" onClick={() => setMenuOpen((open) => !open)}>
                    Open menu
                  </Button>
                  <Menu open={menuOpen}>
                    <MenuItem icon={<Flag size={14} />}>Record solve</MenuItem>
                    <MenuItem icon={<Users size={14} />}>Manage members</MenuItem>
                    <MenuDivider />
                    <MenuItem danger>Remove team</MenuItem>
                  </Menu>
                </div>
              </div>
            </TabsContent>
          </CardContent>
        </Tabs>
      </Card>

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Record a solve"
        description="Submit a flag for one of the open challenges."
        footer={
          <>
            <Button variant="ghost" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => setModalOpen(false)}>Submit</Button>
          </>
        }
      >
        <Input label="Flag" placeholder="flag{...}" />
      </Modal>

      <Drawer open={drawerOpen} onClose={() => setDrawerOpen(false)} title="Team details">
        <p>RedScribe is ranked first with 4,120 points across 34 solves.</p>
      </Drawer>
    </div>
  );
}
