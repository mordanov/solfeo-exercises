import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { i18n } from "../i18n";
import { Button } from "./Ui";
import { ReadOnlyGrid, type ReadOnlyColumn } from "./ReadOnlyGrid";

it("switches between cards and the grid without losing fields, rows or actions", async () => {
  await i18n.changeLanguage("en");
  let mobile = false;
  const listeners = new Set<() => void>();
  vi.stubGlobal("matchMedia", (query: string) => ({
    get matches() {
      return mobile;
    },
    media: query,
    addEventListener: (_event: string, listener: () => void) =>
      listeners.add(listener),
    removeEventListener: (_event: string, listener: () => void) =>
      listeners.delete(listener),
  }));
  const action = vi.fn();
  const rows = Array.from({ length: 50 }, (_, index) => ({
    id: index + 1,
    name: `Record ${index + 1}`,
  }));
  const columns: ReadOnlyColumn<(typeof rows)[number]>[] = [
    {
      field: "name",
      headerName: "Name",
      minWidth: 200,
      render: (row) => row.name,
    },
    {
      field: "actions",
      headerName: "Actions",
      minWidth: 200,
      render: (row) => (
        <Button onClick={() => action(row.id)}>{row.name}</Button>
      ),
    },
  ];
  render(<ReadOnlyGrid rows={rows} columns={columns} label="Records" />);
  expect(screen.getByRole("grid", { name: "Records" })).toBeInTheDocument();
  act(() => {
    mobile = true;
    listeners.forEach((listener) => listener());
  });
  const cards = screen.getByRole("list", { name: "Records" });
  expect(screen.queryByRole("grid")).not.toBeInTheDocument();
  const records = within(cards).getAllByRole("listitem");
  expect(records).toHaveLength(50);
  expect(
    within(records[49])
      .getAllByRole("term")
      .map((element) => element.textContent),
  ).toEqual(["Name", "Actions"]);
  await userEvent.click(
    within(records[49]).getByRole("button", { name: "Record 50" }),
  );
  act(() => {
    mobile = false;
    listeners.forEach((listener) => listener());
  });
  const grid = screen.getByRole("grid", { name: "Records" });
  expect(screen.queryByRole("list")).not.toBeInTheDocument();
  await userEvent.click(
    within(grid).getByRole("button", { name: "Record 50" }),
  );
  expect(action.mock.calls).toEqual([[50], [50]]);
});
