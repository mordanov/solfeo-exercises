import type {
  ButtonHTMLAttributes,
  FormHTMLAttributes,
  HTMLAttributes,
  InputHTMLAttributes,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";
import { Children, cloneElement, isValidElement, useId } from "react";
import Box from "@mui/material/Box";
import MuiButton from "@mui/material/Button";
import Card from "@mui/material/Card";
import Checkbox from "@mui/material/Checkbox";
import NativeSelect from "@mui/material/NativeSelect";
import OutlinedInput from "@mui/material/OutlinedInput";
import TextField from "@mui/material/TextField";
import FormLabel from "@mui/material/FormLabel";
import type { SxProps, Theme } from "@mui/material/styles";

export function Button({
  type = "submit",
  ...props
}: Omit<ButtonHTMLAttributes<HTMLButtonElement>, "color">) {
  return <MuiButton type={type} {...props} />;
}

export function Panel({
  component = "section",
  sx,
  ...props
}: HTMLAttributes<HTMLElement> & {
  component?: "section" | "article" | "li";
  sx?: SxProps<Theme>;
}) {
  return <Card component={component} {...props} sx={sx} />;
}

export function Form(props: FormHTMLAttributes<HTMLFormElement>) {
  return (
    <Box
      component="form"
      {...props}
      sx={{
        display: "grid",
        gridTemplateColumns: "minmax(0, 1fr)",
        gap: 2,
        maxWidth: 560,
        minWidth: 0,
        my: 2,
      }}
    />
  );
}

export function Field({ children, ...props }: HTMLAttributes<HTMLElement>) {
  const id = useId();
  const parts = Children.toArray(children);
  const controls = parts.filter(isValidElement<{ id?: string; type?: string }>);
  const label = parts.filter((part) => !isValidElement(part));
  const checkbox = controls.some(
    (control) => control.props.type === "checkbox",
  );
  return (
    <Box
      {...props}
      sx={{
        display: "flex",
        flexDirection: checkbox ? "row" : "column",
        gap: 1,
        fontSize: "0.9rem",
        fontWeight: 500,
        minWidth: 0,
        alignItems: checkbox ? "center" : undefined,
      }}
    >
      {!checkbox && <FormLabel htmlFor={id}>{label}</FormLabel>}
      {controls.map((control) => cloneElement(control, { id }))}
      {checkbox && <FormLabel htmlFor={id}>{label}</FormLabel>}
    </Box>
  );
}

// Preserve native input attributes and event signatures at the presentation boundary.
export function Input({
  type = "text",
  value,
  checked,
  onChange,
  disabled,
  required,
  autoComplete,
  ...native
}: InputHTMLAttributes<HTMLInputElement>) {
  if (type === "checkbox") {
    return (
      <Checkbox
        checked={checked}
        onChange={onChange}
        disabled={disabled}
        required={required}
        slotProps={{ input: native }}
      />
    );
  }
  return (
    <TextField
      fullWidth
      type={type}
      value={value}
      onChange={onChange}
      disabled={disabled}
      required={required}
      autoComplete={autoComplete}
      slotProps={{ htmlInput: native }}
    />
  );
}

export function Select({
  children,
  value,
  onChange,
  disabled,
  required,
  ...native
}: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <NativeSelect
      value={value}
      onChange={onChange}
      disabled={disabled}
      required={required}
      input={<OutlinedInput />}
      inputProps={native}
      sx={{
        width: "100%",
        minWidth: 0,
        "& select": { textOverflow: "ellipsis" },
      }}
    >
      {children}
    </NativeSelect>
  );
}

export function Textarea({
  value,
  onChange,
  disabled,
  required,
  ...native
}: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <TextField
      fullWidth
      multiline
      minRows={4}
      value={value}
      onChange={onChange}
      disabled={disabled}
      required={required}
      slotProps={{ htmlInput: native }}
    />
  );
}
