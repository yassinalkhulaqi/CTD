import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { AreaChart, BarChart, DonutChart, Heatmap, Sparkline } from "./Charts";

describe("BarChart", () => {
  it("renders an accessible figure", () => {
    render(<BarChart values={[1, 2, 3]} label="Solves per hour" />);
    expect(screen.getByRole("img", { name: /Solves per hour/ })).toBeInTheDocument();
  });

  it("renders a placeholder without data", () => {
    render(<BarChart values={[]} label="Solves per hour" />);
    expect(screen.getByText("No data to display")).toBeInTheDocument();
  });
});

describe("AreaChart", () => {
  it("renders the series", () => {
    render(<AreaChart values={[4, 8, 2]} label="Velocity" />);
    expect(screen.getByRole("img", { name: /Velocity/ })).toBeInTheDocument();
  });
});

describe("DonutChart", () => {
  it("renders the legend of every slice", () => {
    render(
      <DonutChart
        slices={[
          { label: "Web", value: 3, color: "#38bdf8" },
          { label: "Crypto", value: 1, color: "#c084fc" },
        ]}
        label="Challenge mix"
        centreLabel="4"
      />,
    );
    expect(screen.getByText("Web")).toBeInTheDocument();
    expect(screen.getByText("Crypto")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
  });

  it("renders a placeholder without slices", () => {
    render(<DonutChart slices={[]} label="Challenge mix" />);
    expect(screen.getByText("No data to display")).toBeInTheDocument();
  });
});

describe("Heatmap", () => {
  it("renders a cell per bucket", () => {
    const matrix = [
      [0, 1, 2],
      [3, 4, 5],
    ];
    render(<Heatmap matrix={matrix} label="Activity heatmap" />);
    expect(screen.getAllByRole("button")).toHaveLength(6);
  });
});

describe("Sparkline", () => {
  it("renders an accessible image", () => {
    render(<Sparkline values={[1, 2, 3]} label="Trend" />);
    expect(screen.getByRole("img", { name: "Trend" })).toBeInTheDocument();
  });
});
