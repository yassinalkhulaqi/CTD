/**
 * The 404 page.
 */

import { Link } from "react-router-dom";
import { Compass } from "lucide-react";
import { Button, Card, CardContent, EmptyState } from "../../components/ui";
import styles from "./NotFoundPage.module.css";

/**
 * Render the not found page.
 *
 * @returns The page element.
 */
export default function NotFoundPage() {
  return (
    <div className={styles.page}>
      <Card>
        <CardContent>
          <EmptyState
            icon={<Compass size={22} />}
            title="This screen does not exist"
            description="The address you followed points to a page that is not part of the dashboard."
            action={
              <Link to="/">
                <Button size="sm">Back to the overview</Button>
              </Link>
            }
          />
        </CardContent>
      </Card>
    </div>
  );
}
