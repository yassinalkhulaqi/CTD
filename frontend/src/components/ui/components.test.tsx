import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { Button, IconButton } from "./Button";
import { Badge } from "./Display";
import { Input, Select } from "./Field";
import { EmptyState, Progress, ScoreRing } from "./Feedback";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./Tabs";

describe("Button", () => {
  it("renders its label", () => {
    render(<Button>Record solve</Button>);
    expect(
      screen.getByRole("button", { name: "Record solve" }),
    ).toBeInTheDocument();
  });

  it("disables itself while loading", () => {
    render(
      <Button loading loadingLabel="Saving…">
        Save
      </Button>,
    );
    const button = screen.getByRole("button");
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
  });

  it("calls the click handler", () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Go</Button>);
    fireEvent.click(screen.getByRole("button"));
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});

describe("IconButton", () => {
  it("exposes an accessible label", () => {
    render(<IconButton icon={<span>x</span>} label="Notifications" />);
    expect(
      screen.getByRole("button", { name: "Notifications" }),
    ).toBeInTheDocument();
  });
});

describe("Badge", () => {
  it("renders its content", () => {
    render(<Badge tone="success">Solved</Badge>);
    expect(screen.getByText("Solved")).toBeInTheDocument();
  });
});

describe("Input", () => {
  it("associates the label with the control", () => {
    render(<Input label="Handle" hint="Lowercase" />);
    const input = screen.getByLabelText("Handle");
    expect(input).toHaveAttribute("aria-describedby");
  });

  it("marks the control invalid when an error is present", () => {
    render(<Input label="Flag" error="Bad format" />);
    expect(screen.getByLabelText("Flag")).toHaveAttribute(
      "aria-invalid",
      "true",
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Bad format");
  });
});

describe("Select", () => {
  it("renders the provided options", () => {
    render(
      <Select
        label="Category"
        options={[
          { value: "web", label: "Web" },
          { value: "pwn", label: "Binary" },
        ]}
      />,
    );
    expect(screen.getByRole("option", { name: "Web" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Binary" })).toBeInTheDocument();
  });
});

describe("Progress", () => {
  it("exposes the completion ratio", () => {
    render(<Progress value={42} label="Completion" />);
    expect(screen.getByRole("progressbar")).toHaveAttribute(
      "aria-valuenow",
      "42",
    );
  });
});

describe("ScoreRing", () => {
  it("labels the completion percentage", () => {
    render(<ScoreRing value={0.5} />);
    expect(
      screen.getByRole("img", { name: "50% complete" }),
    ).toBeInTheDocument();
  });
});

describe("EmptyState", () => {
  it("renders the title and description", () => {
    render(
      <EmptyState title="No solves" description="Record the first flag." />,
    );
    expect(screen.getByText("No solves")).toBeInTheDocument();
    expect(screen.getByText("Record the first flag.")).toBeInTheDocument();
  });
});

describe("Tabs", () => {
  it("switches the visible panel", () => {
    render(
      <Tabs value="one" onValueChange={() => undefined} label="Sections">
        <TabsList>
          <TabsTrigger value="one">One</TabsTrigger>
          <TabsTrigger value="two">Two</TabsTrigger>
        </TabsList>
        <TabsContent value="one">First panel</TabsContent>
        <TabsContent value="two">Second panel</TabsContent>
      </Tabs>,
    );

    expect(screen.getByText("First panel")).toBeInTheDocument();
    expect(screen.queryByText("Second panel")).not.toBeInTheDocument();
  });
});
