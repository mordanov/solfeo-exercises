import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  createUser,
  listUsers,
  updateUser,
  resetPassword,
  type Auth,
  type Role,
  type User,
} from "../../api/auth";
import { ErrorMessage } from "../../components/AccountUi";
import { Button, Field, Form, Input, Panel, Select } from "../../components/Ui";
import {
  ReadOnlyGrid,
  type ReadOnlyColumn,
} from "../../components/ReadOnlyGrid";
import Box from "@mui/material/Box";
import Alert from "@mui/material/Alert";

function RoleOptions() {
  const { t } = useTranslation();
  return (
    <>
      <option value="student">{t("roles.student")}</option>
      <option value="manager">{t("roles.manager")}</option>
    </>
  );
}

function UserEditor({
  auth,
  user,
  onDone,
}: {
  auth: Auth;
  user: User;
  onDone: () => void;
}) {
  const { t } = useTranslation();
  const [first, setFirst] = useState(user.first_name);
  const [last, setLast] = useState(user.last_name);
  const [role, setRole] = useState<Role>(user.role);
  const [password, setPassword] = useState("");
  const [mustChange, setMustChange] = useState(true);
  const update = useMutation({
    mutationFn: () =>
      updateUser(auth.csrf_token, user.id, {
        first_name: first,
        last_name: last,
        role,
      }),
    onSuccess: onDone,
  });
  const reset = useMutation({
    mutationFn: () =>
      resetPassword(auth.csrf_token, user.id, password, mustChange),
    onSuccess: () => {
      setPassword("");
      onDone();
    },
  });
  return (
    <Panel aria-label={t("users.editUser", { username: user.username })}>
      <h3>{t("users.editUser", { username: user.username })}</h3>
      <Form
        onSubmit={(event) => {
          event.preventDefault();
          update.mutate();
        }}
      >
        <Field>
          {t("users.firstName")}
          <Input
            required
            maxLength={100}
            value={first}
            onChange={(event) => setFirst(event.target.value)}
          />
        </Field>
        <Field>
          {t("users.lastName")}
          <Input
            required
            maxLength={100}
            value={last}
            onChange={(event) => setLast(event.target.value)}
          />
        </Field>
        <Field>
          {t("users.role")}
          <Select
            value={role}
            onChange={(event) => {
              if (
                event.target.value === "manager" ||
                event.target.value === "student"
              )
                setRole(event.target.value);
            }}
          >
            <RoleOptions />
          </Select>
        </Field>
        <Button disabled={update.isPending}>{t("users.save")}</Button>
        {update.isError && <ErrorMessage error={update.error} />}
      </Form>
      <Form
        onSubmit={(event) => {
          event.preventDefault();
          reset.mutate();
        }}
      >
        <Field>
          {t("users.temporaryPassword")}
          <Input
            required
            type="password"
            autoComplete="new-password"
            maxLength={256}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </Field>
        <Field>
          <Input
            type="checkbox"
            checked={mustChange}
            onChange={(event) => setMustChange(event.target.checked)}
          />
          {t("users.mustChange")}
        </Field>
        <Button disabled={reset.isPending}>{t("users.resetPassword")}</Button>
        {reset.isError && <ErrorMessage error={reset.error} />}
      </Form>
      <Button onClick={onDone}>{t("common.close")}</Button>
    </Panel>
  );
}

export function Users({ auth }: { auth: Auth }) {
  const { t, i18n } = useTranslation();
  const cache = useQueryClient();
  const [offset, setOffset] = useState(0);
  const query = useQuery({
    queryKey: ["users", auth.user.id, offset],
    queryFn: ({ signal }) => listUsers(offset, signal),
    retry: false,
  });
  const [username, setUsername] = useState("");
  const [first, setFirst] = useState("");
  const [last, setLast] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("student");
  const [mustChange, setMustChange] = useState(true);
  const [editing, setEditing] = useState<User | null>(null);
  const refresh = () => void cache.invalidateQueries({ queryKey: ["users"] });
  const creation = useMutation({
    mutationFn: () =>
      createUser(auth.csrf_token, {
        username,
        first_name: first,
        last_name: last,
        password,
        role,
        must_change_password: mustChange,
      }),
    onSuccess: () => {
      setUsername("");
      setFirst("");
      setLast("");
      setPassword("");
      refresh();
    },
  });
  const activation = useMutation({
    mutationFn: (user: User) =>
      updateUser(auth.csrf_token, user.id, { is_active: !user.is_active }),
    onSuccess: refresh,
  });
  const columns: ReadOnlyColumn<User>[] = [
    {
      field: "username",
      headerName: t("auth.username"),
      minWidth: 160,
      flex: 1,
      render: (user) => (
        <span>
          {user.username}
          {user.is_emergency && <span> ({t("users.emergency")})</span>}
        </span>
      ),
    },
    {
      field: "name",
      headerName: t("users.name"),
      minWidth: 180,
      flex: 1,
      render: (user) => (
        <span>
          {user.first_name} {user.last_name}
        </span>
      ),
    },
    {
      field: "role",
      headerName: t("users.role"),
      minWidth: 120,
      render: (user) => t(`roles.${user.role}`),
    },
    {
      field: "status",
      headerName: t("users.status"),
      minWidth: 120,
      render: (user) => t(user.is_active ? "users.active" : "users.inactive"),
    },
    {
      field: "actions",
      headerName: t("users.actions"),
      minWidth: 250,
      flex: 1,
      render: (user) =>
        !user.is_emergency &&
        user.id !== auth.user.id && (
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
            <Button
              aria-label={t("users.editUser", { username: user.username })}
              onClick={() => setEditing(user)}
            >
              {t("users.edit")}
            </Button>
            <Button
              style={{ width: "12em" }}
              disabled={activation.isPending}
              aria-label={t(
                user.is_active ? "users.deactivateUser" : "users.activateUser",
                { username: user.username },
              )}
              onClick={() => activation.mutate(user)}
            >
              {t(user.is_active ? "users.deactivate" : "users.activate")}
            </Button>
          </Box>
        ),
    },
  ];
  return (
    <Panel>
      <h2>{t("users.title")}</h2>
      {query.isPending && <p aria-live="polite">{t("common.loading")}</p>}
      {query.isError && (
        <>
          <ErrorMessage error={query.error} />
          <Button onClick={() => void query.refetch()}>
            {t("common.retry")}
          </Button>
        </>
      )}
      {query.data && !query.isError && (
        <>
          <p>
            {t("users.total", {
              total: new Intl.NumberFormat(i18n.language).format(
                query.data.total,
              ),
            })}
          </p>
          <ReadOnlyGrid
            rows={query.data.users}
            columns={columns}
            label={t("users.title")}
          />
          <Button
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - 50))}
          >
            {t("common.previous")}
          </Button>{" "}
          <Button
            disabled={offset + 50 >= query.data.total}
            onClick={() => setOffset(offset + 50)}
          >
            {t("common.next")}
          </Button>
        </>
      )}
      {activation.isError && <ErrorMessage error={activation.error} />}
      {editing ? (
        <UserEditor
          key={editing.id}
          auth={auth}
          user={editing}
          onDone={() => {
            setEditing(null);
            refresh();
          }}
        />
      ) : (
        <>
          <h3>{t("users.create")}</h3>
          <Form
            onSubmit={(event) => {
              event.preventDefault();
              creation.mutate();
            }}
          >
            <Field>
              {t("auth.username")}
              <Input
                required
                autoComplete="off"
                maxLength={64}
                value={username}
                onChange={(event) => setUsername(event.target.value)}
              />
            </Field>
            <Field>
              {t("users.firstName")}
              <Input
                required
                autoComplete="off"
                maxLength={100}
                value={first}
                onChange={(event) => setFirst(event.target.value)}
              />
            </Field>
            <Field>
              {t("users.lastName")}
              <Input
                required
                autoComplete="off"
                maxLength={100}
                value={last}
                onChange={(event) => setLast(event.target.value)}
              />
            </Field>
            <Field>
              {t("users.temporaryPassword")}
              <Input
                required
                type="password"
                autoComplete="new-password"
                maxLength={256}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </Field>
            <p>{t("auth.passwordHint")}</p>
            <Field>
              {t("users.role")}
              <Select
                value={role}
                onChange={(event) => {
                  if (
                    event.target.value === "manager" ||
                    event.target.value === "student"
                  )
                    setRole(event.target.value);
                }}
              >
                <RoleOptions />
              </Select>
            </Field>
            <Field>
              <Input
                type="checkbox"
                checked={mustChange}
                onChange={(event) => setMustChange(event.target.checked)}
              />
              {t("users.mustChange")}
            </Field>
            <Button disabled={creation.isPending}>{t("users.create")}</Button>
            {creation.isError && <ErrorMessage error={creation.error} />}
            {creation.isSuccess && (
              <Alert severity="success" role="status">
                {t("users.created")}
              </Alert>
            )}
          </Form>
        </>
      )}
    </Panel>
  );
}
