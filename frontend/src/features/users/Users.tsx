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
    <section aria-label={t("users.editUser", { username: user.username })}>
      <h3>{t("users.editUser", { username: user.username })}</h3>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          update.mutate();
        }}
      >
        <label>
          {t("users.firstName")}
          <input
            required
            maxLength={100}
            value={first}
            onChange={(event) => setFirst(event.target.value)}
          />
        </label>
        <label>
          {t("users.lastName")}
          <input
            required
            maxLength={100}
            value={last}
            onChange={(event) => setLast(event.target.value)}
          />
        </label>
        <label>
          {t("users.role")}
          <select
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
          </select>
        </label>
        <button disabled={update.isPending}>{t("users.save")}</button>
        {update.isError && <ErrorMessage error={update.error} />}
      </form>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          reset.mutate();
        }}
      >
        <label>
          {t("users.temporaryPassword")}
          <input
            required
            type="password"
            autoComplete="new-password"
            maxLength={256}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        <label>
          <input
            type="checkbox"
            checked={mustChange}
            onChange={(event) => setMustChange(event.target.checked)}
          />
          {t("users.mustChange")}
        </label>
        <button disabled={reset.isPending}>{t("users.resetPassword")}</button>
        {reset.isError && <ErrorMessage error={reset.error} />}
      </form>
      <button onClick={onDone}>{t("common.close")}</button>
    </section>
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
  return (
    <section>
      <h2>{t("users.title")}</h2>
      {query.isPending && <p aria-live="polite">{t("common.loading")}</p>}
      {query.isError && (
        <>
          <ErrorMessage error={query.error} />
          <button onClick={() => void query.refetch()}>
            {t("common.retry")}
          </button>
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
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>{t("auth.username")}</th>
                  <th>{t("users.name")}</th>
                  <th>{t("users.role")}</th>
                  <th>{t("users.status")}</th>
                  <th>{t("users.actions")}</th>
                </tr>
              </thead>
              <tbody>
                {query.data.users.map((user) => (
                  <tr key={user.id}>
                    <td>
                      {user.username}
                      {user.is_emergency && (
                        <span> ({t("users.emergency")})</span>
                      )}
                    </td>
                    <td>
                      {user.first_name} {user.last_name}
                    </td>
                    <td>{t(`roles.${user.role}`)}</td>
                    <td>
                      {t(user.is_active ? "users.active" : "users.inactive")}
                    </td>
                    <td>
                      {!user.is_emergency && user.id !== auth.user.id && (
                        <>
                          <button
                            aria-label={t("users.editUser", {
                              username: user.username,
                            })}
                            onClick={() => setEditing(user)}
                          >
                            {t("users.edit")}
                          </button>{" "}
                          <button
                            disabled={activation.isPending}
                            aria-label={t(
                              user.is_active
                                ? "users.deactivateUser"
                                : "users.activateUser",
                              { username: user.username },
                            )}
                            onClick={() => activation.mutate(user)}
                          >
                            {t(
                              user.is_active
                                ? "users.deactivate"
                                : "users.activate",
                            )}
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - 50))}
          >
            {t("common.previous")}
          </button>{" "}
          <button
            disabled={offset + 50 >= query.data.total}
            onClick={() => setOffset(offset + 50)}
          >
            {t("common.next")}
          </button>
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
          <form
            onSubmit={(event) => {
              event.preventDefault();
              creation.mutate();
            }}
          >
            <label>
              {t("auth.username")}
              <input
                required
                autoComplete="off"
                maxLength={64}
                value={username}
                onChange={(event) => setUsername(event.target.value)}
              />
            </label>
            <label>
              {t("users.firstName")}
              <input
                required
                autoComplete="off"
                maxLength={100}
                value={first}
                onChange={(event) => setFirst(event.target.value)}
              />
            </label>
            <label>
              {t("users.lastName")}
              <input
                required
                autoComplete="off"
                maxLength={100}
                value={last}
                onChange={(event) => setLast(event.target.value)}
              />
            </label>
            <label>
              {t("users.temporaryPassword")}
              <input
                required
                type="password"
                autoComplete="new-password"
                maxLength={256}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </label>
            <p>{t("auth.passwordHint")}</p>
            <label>
              {t("users.role")}
              <select
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
              </select>
            </label>
            <label>
              <input
                type="checkbox"
                checked={mustChange}
                onChange={(event) => setMustChange(event.target.checked)}
              />
              {t("users.mustChange")}
            </label>
            <button disabled={creation.isPending}>{t("users.create")}</button>
            {creation.isError && <ErrorMessage error={creation.error} />}
            {creation.isSuccess && <p role="status">{t("users.created")}</p>}
          </form>
        </>
      )}
    </section>
  );
}
