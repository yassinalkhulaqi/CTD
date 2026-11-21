import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TemplatePicker } from "./TemplatePicker";
import { TEMPLATE } from "../testFixtures";

describe("TemplatePicker", () => {
  it("renders the selected template details", () => {
    render(
      <TemplatePicker
        templates={[TEMPLATE]}
        selectedId={TEMPLATE.id}
        onSelect={() => undefined}
      />,
    );
    expect(screen.getByLabelText("Report template")).toHaveValue(TEMPLATE.id);
    expect(screen.getByText(TEMPLATE.description)).toBeInTheDocument();
    expect(screen.getByText("Team")).toBeInTheDocument();
    expect(screen.getByText("3 sections")).toBeInTheDocument();
  });

  it("calls the selection callback when another template is chosen", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const second = {
      ...TEMPLATE,
      id: "tpl-2",
      name: "Event recap",
      section_count: 5,
    };
    render(
      <TemplatePicker
        templates={[TEMPLATE, second]}
        selectedId={TEMPLATE.id}
        onSelect={onSelect}
      />,
    );
    await user.selectOptions(screen.getByLabelText("Report template"), "tpl-2");
    expect(onSelect).toHaveBeenCalledWith(second);
  });

  it("renders an empty state when no templates exist", () => {
    render(
      <TemplatePicker
        templates={[]}
        selectedId=""
        onSelect={() => undefined}
      />,
    );
    expect(screen.getByText("No templates yet")).toBeInTheDocument();
  });

  it("renders skeletons while loading", () => {
    const { container } = render(
      <TemplatePicker
        templates={[]}
        selectedId=""
        onSelect={() => undefined}
        loading
      />,
    );
    expect(container.querySelector('[aria-busy="true"]')).not.toBeNull();
  });
});
