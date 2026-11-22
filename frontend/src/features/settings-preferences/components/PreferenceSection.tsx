import type { ReactNode } from "react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "../../../components/ui";
import styles from "../PreferencesPage.module.css";

interface Props {
  title: string;
  description: string;
  children: ReactNode;
}

export function PreferenceSection({ title, description, children }: Props) {
  return (
    <Card className={styles.sectionCard}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className={styles.sectionContent}>{children}</CardContent>
    </Card>
  );
}
