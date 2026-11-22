/**
 * A detailed card for a single roster member.
 */

import { useState } from "react";
import { CalendarClock, MoreHorizontal, Trash2 } from "lucide-react";
import { cn } from "../../../lib/utils";
import {
  Avatar,
  Card,
  IconButton,
  Menu,
  MenuDivider,
  MenuItem,
  Popover,
  StatusDot,
} from "../../../components/ui";
import { ROLE_OPTIONS, availabilityLabel, availabilityTone } from "../domain";
import type { RosterMember, RosterRole } from "../types";
import { CapacityBar } from "./CapacityBar";
import { RoleChip } from "./RoleChip";
import styles from "./MemberCard.module.css";

/** Props accepted by {@link MemberCard}. */
export interface MemberCardProps {
  /** The member to present. */
  member: RosterMember;
  /** Hours reserved for the member. */
  assignedHours: number;
  /** Called when a new role is chosen. */
  onRoleChange: (member: RosterMember, role: RosterRole) => void;
  /** Called when the member should be removed. */
  onRemove: (member: RosterMember) => void;
  /** Disable controls while a mutation is running. */
  busy?: boolean;
  /** Additional class applied to the card. */
  className?: string;
}

/**
 * Render a member as a rich card with a role menu and capacity meter.
 *
 * @param props - The component props.
 * @returns The member card element.
 */
export function MemberCard({
  member,
  assignedHours,
  onRoleChange,
  onRemove,
  busy = false,
  className,
}: MemberCardProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const presence =
    member.availability === "available"
      ? "online"
      : member.availability === "busy"
        ? "away"
        : "offline";

  function selectRole(role: RosterRole) {
    setMenuOpen(false);
    if (role !== member.role) onRoleChange(member, role);
  }

  return (
    <Card className={cn(styles.card, className)} as="article">
      <div className={styles.header}>
        <Avatar
          name={member.display_name || member.handle}
          presence={presence}
          size="md"
        />
        <div className={styles.identity}>
          <span className={styles.name}>{member.display_name}</span>
          <span className={styles.handle}>@{member.handle}</span>
        </div>
        <Popover
          align="end"
          open={menuOpen}
          onClose={() => setMenuOpen(false)}
          trigger={
            <IconButton
              icon={<MoreHorizontal size={18} />}
              label={`Role options for ${member.handle}`}
              disabled={busy}
              onClick={() => setMenuOpen((current) => !current)}
            />
          }
        >
          <Menu open={menuOpen} width={190}>
            <p className={styles.menuTitle}>Change role</p>
            {ROLE_OPTIONS.map((option) => (
              <MenuItem
                key={option.value}
                active={option.value === member.role}
                onClick={() => selectRole(option.value)}
              >
                {option.label}
              </MenuItem>
            ))}
            <MenuDivider />
            <MenuItem
              danger
              icon={<Trash2 size={14} />}
              onClick={() => {
                setMenuOpen(false);
                onRemove(member);
              }}
            >
              Remove member
            </MenuItem>
          </Menu>
        </Popover>
      </div>

      <div className={styles.badges}>
        <RoleChip role={member.role} />
        <span className={styles.availability}>
          <StatusDot
            tone={availabilityTone(member.availability)}
            pulse={presence === "online"}
          />
          {availabilityLabel(member.availability)}
        </span>
      </div>

      {member.specialty ? (
        <p className={styles.specialty}>{member.specialty}</p>
      ) : null}

      <div className={styles.timezone}>
        <CalendarClock size={13} aria-hidden="true" />
        {member.timezone}
      </div>

      <CapacityBar
        assignedHours={assignedHours}
        capacityHours={member.capacity_hours}
        label={`Capacity for ${member.handle}`}
        className={styles.capacity}
      />
    </Card>
  );
}
