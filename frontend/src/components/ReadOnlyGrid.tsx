import {
  DataGrid,
  type GridColDef,
  type GridValidRowModel,
} from "@mui/x-data-grid";
import { enUS, esES, ruRU } from "@mui/x-data-grid/locales";
import { useTranslation } from "react-i18next";

function EmptyOverlay() {
  return null;
}

export function ReadOnlyGrid<Row extends GridValidRowModel>({
  rows,
  columns,
  label,
}: {
  rows: Row[];
  columns: GridColDef<Row>[];
  label: string;
}) {
  const { i18n } = useTranslation();
  const locale =
    i18n.resolvedLanguage === "ru"
      ? ruRU
      : i18n.resolvedLanguage === "es"
        ? esES
        : enUS;
  return (
    <DataGrid<Row>
      aria-label={label}
      rows={rows}
      columns={columns}
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
