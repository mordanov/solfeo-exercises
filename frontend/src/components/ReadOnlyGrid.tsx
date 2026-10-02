import {
  DataGrid,
  type GridColDef,
  type GridValidRowModel,
} from "@mui/x-data-grid";
import { enUS, esES, ruRU } from "@mui/x-data-grid/locales";
import { useTranslation } from "react-i18next";
import type { ReactNode } from "react";
import Box from "@mui/material/Box";
import useMediaQuery from "@mui/material/useMediaQuery";
import { useTheme } from "@mui/material/styles";

export type ReadOnlyColumn<Row extends GridValidRowModel> = Pick<
  GridColDef<Row>,
  "field" | "minWidth" | "flex"
> & {
  headerName: string;
  render: (row: Row) => ReactNode;
};

function EmptyOverlay() {
  return null;
}

export function ReadOnlyGrid<Row extends GridValidRowModel>({
  rows,
  columns,
  label,
}: {
  rows: Row[];
  columns: ReadOnlyColumn<Row>[];
  label: string;
}) {
  const { i18n } = useTranslation();
  const theme = useTheme();
  const mobile = useMediaQuery(theme.breakpoints.down("sm"));
  const locale =
    i18n.resolvedLanguage === "ru"
      ? ruRU
      : i18n.resolvedLanguage === "es"
        ? esES
        : enUS;
  if (mobile) {
    return (
      <Box
        component="ul"
        aria-label={label}
        sx={{ listStyle: "none", p: 0, my: 2 }}
      >
        {rows.map((row) => (
          <Box
            component="li"
            key={row.id}
            sx={{
              p: 1.5,
              mb: 2,
              border: 1,
              borderColor: "divider",
              borderRadius: 1,
              minWidth: 0,
            }}
          >
            <Box component="dl" sx={{ m: 0, display: "grid", gap: 1.5 }}>
              {columns.map((column) => (
                <Box key={column.field} sx={{ minWidth: 0 }}>
                  <Box
                    component="dt"
                    sx={{
                      color: "text.secondary",
                      fontSize: "0.875rem",
                      fontWeight: 500,
                    }}
                  >
                    {column.headerName}
                  </Box>
                  <Box
                    component="dd"
                    sx={{ m: 0, mt: 0.5, overflowWrap: "anywhere" }}
                  >
                    {column.render(row)}
                  </Box>
                </Box>
              ))}
            </Box>
          </Box>
        ))}
      </Box>
    );
  }
  const gridColumns: GridColDef<Row>[] = columns.map(
    ({ render, ...column }) => ({
      ...column,
      renderCell: ({ row }) => render(row),
    }),
  );
  return (
    <DataGrid<Row>
      aria-label={label}
      rows={rows}
      columns={gridColumns}
      autoHeight
      disableVirtualization
      disableEval
      disableColumnSorting
      disableColumnFilter
      disableColumnMenu
      disableColumnSelector
      disableColumnResize
      disableDensitySelector
      rowSelection={false}
      hideFooter
      paginationModel={{ page: 0, pageSize: 100 }}
      getRowHeight={() => "auto"}
      slots={{ noRowsOverlay: EmptyOverlay }}
      localeText={locale.components.MuiDataGrid.defaultProps.localeText}
      sx={{
        my: 2,
        border: 0,
        "& .MuiDataGrid-columnHeaders": { bgcolor: "action.hover" },
        "& .MuiDataGrid-cell": {
          py: 1.5,
          whiteSpace: "normal",
          overflowWrap: "anywhere",
          display: "flex",
          alignItems: "center",
        },
      }}
    />
  );
}
