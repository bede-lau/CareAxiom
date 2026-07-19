import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { regions } from "../demoData";
import { IndiaMap } from "./IndiaMap";

describe("IndiaMap", () => {
  it("supports keyboard selection and exposes the table-alternative description", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(
      <IndiaMap
        regions={regions.slice(0, 2)}
        selectedId={regions[0].id}
        crisisEnabled={false}
        onSelect={onSelect}
      />,
    );

    const patna = screen.getByRole("button", {
      name: /Patna 800001: Strong nearby documentary support/i,
    });
    patna.focus();
    await user.keyboard("{Enter}");

    expect(onSelect).toHaveBeenCalledWith(regions[1]);
    expect(screen.getByText(/Not PIN centroids or population origins/i)).toBeInTheDocument();
  });
});
