/** Rendered interaction tests for the message editor. */

import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MessageEditor } from "./components/MessageEditor";
import type { Locale, MessageDraft } from "./types";

const locales: Locale[] = [
  {
    code: "en",
    name: "English",
    direction: "ltr",
    plural_rules: "simple",
    base_language: "en",
    canonical_code: "en",
    is_rtl: false,
    chain: ["en"],
  },
];

const draft: MessageDraft = {
  locale: "en",
  namespace: "ui",
  key: "greeting",
  value: "Hello, {name}!",
};

describe("MessageEditor", () => {
  it("shows detected placeholders and a qualified key", () => {
    render(
      <MessageEditor
        locales={locales}
        draft={draft}
        onChange={() => undefined}
        onSave={() => undefined}
      />,
    );
    expect(screen.getByText("{name}")).toBeInTheDocument();
    expect(screen.getByText("ui:greeting")).toBeInTheDocument();
  });

  it("reports changes to the draft", () => {
    const onChange = vi.fn();
    render(
      <MessageEditor
        locales={locales}
        draft={draft}
        onChange={onChange}
        onSave={() => undefined}
      />,
    );
    fireEvent.change(screen.getByLabelText("Message"), {
      target: { value: "Hi {name}, you have {count}" },
    });
    expect(onChange).toHaveBeenCalledWith({
      ...draft,
      value: "Hi {name}, you have {count}",
    });
  });

  it("normalises keys and saves a valid draft", () => {
    const onChange = vi.fn();
    const onSave = vi.fn();
    render(
      <MessageEditor
        locales={locales}
        draft={draft}
        onChange={onChange}
        onSave={onSave}
      />,
    );
    fireEvent.change(screen.getByLabelText("Key"), {
      target: { value: "fare well" },
    });
    expect(onChange).toHaveBeenCalledWith({ ...draft, key: "fare-well" });
    fireEvent.click(screen.getByRole("button", { name: /Save message/ }));
    expect(onSave).toHaveBeenCalled();
  });

  it("disables saving when the draft is incomplete", () => {
    render(
      <MessageEditor
        locales={locales}
        draft={{ ...draft, key: "" }}
        onChange={() => undefined}
        onSave={() => undefined}
      />,
    );
    expect(screen.getByRole("button", { name: /Save message/ })).toBeDisabled();
  });

  it("renders a server error message", () => {
    render(
      <MessageEditor
        locales={locales}
        draft={draft}
        onChange={() => undefined}
        onSave={() => undefined}
        error="Key is invalid"
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Key is invalid");
  });
});
