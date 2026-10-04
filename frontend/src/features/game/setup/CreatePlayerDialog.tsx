import {
  Box,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Typography,
} from "@mui/material";
import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { type Auth } from "../../../api/auth";
import { ErrorMessage } from "../../../components/AccountUi";
import { Button, Field, Form, Input, Select } from "../../../components/Ui";
import { useCreatePlayer, useEligibleAccounts } from "../api/hooks";

export default function CreatePlayerDialog({
  auth,
  onClose,
}: {
  auth: Auth;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [name, setName] = useState("");
  const [selected, setSelected] = useState<number | null>(null);
  const [offset, setOffset] = useState(0);
  const accounts = useEligibleAccounts(offset);
  const create = useCreatePlayer();
  const options = accounts.data?.users ?? [];
  const account = options.find((user) => user.id === selected) ?? options[0];
  useEffect(() => {
    if (accounts.data && offset > 0 && offset >= accounts.data.total)
      setOffset(0);
  }, [accounts.data, offset]);
  function submit(event: FormEvent) {
    event.preventDefault();
    if (!name.trim() || !account) return;
    create.mutate(
      {
        csrf: auth.csrf_token,
        name: name.trim(),
        avatar_animal: "unicorn",
        account_id: account.id,
      },
      { onSuccess: onClose },
    );
  }
  return (
    <Dialog
      open
      onClose={create.isPending ? undefined : onClose}
      fullWidth
      maxWidth="sm"
    >
      <DialogTitle>{t("game.players.create")}</DialogTitle>
      {accounts.isPending || accounts.isError || !account ? (
        <>
          <DialogContent>
            {accounts.isError ? (
              <>
                <ErrorMessage error={accounts.error} />
                <Button onClick={() => void accounts.refetch()}>
                  {t("common.retry")}
                </Button>
              </>
            ) : (
              <Typography role="status">
                {t(
                  accounts.data?.total === 0
                    ? "game.players.allAssigned"
                    : "common.loading",
                )}
              </Typography>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={onClose}>{t("common.close")}</Button>
          </DialogActions>
        </>
      ) : (
        <Form onSubmit={submit}>
          <DialogContent>
            <Field>
              {t("game.players.name")}
              <Input
                autoFocus
                required
                maxLength={20}
                value={name}
                onChange={(event) => setName(event.target.value)}
                disabled={create.isPending}
              />
            </Field>
            <Field>
              {t("game.players.account")}
              <Select
                value={account.id}
                disabled={accounts.isFetching || create.isPending}
                onChange={(event) => {
                  setSelected(Number(event.target.value));
                }}
              >
                {options.map((user) => (
                  <option key={user.id} value={user.id}>
                    {t("game.players.accountLabel", {
                      first: user.first_name,
                      last: user.last_name,
                      username: user.username,
                    })}
                  </option>
                ))}
              </Select>
            </Field>
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mt: 1 }}>
              <Button
                type="button"
                disabled={
                  offset === 0 || accounts.isFetching || create.isPending
                }
                onClick={() => setOffset((value) => Math.max(0, value - 50))}
              >
                {t("common.previous")}
              </Button>
              <Button
                type="button"
                disabled={
                  !accounts.data ||
                  offset + 50 >= accounts.data.total ||
                  accounts.isFetching ||
                  create.isPending
                }
                onClick={() => setOffset((value) => value + 50)}
              >
                {t("common.next")}
              </Button>
            </Box>
            {create.isError && <ErrorMessage error={create.error} />}
          </DialogContent>
          <DialogActions>
            <Button type="button" disabled={create.isPending} onClick={onClose}>
              {t("common.close")}
            </Button>
            <Button
              disabled={
                !name.trim() ||
                create.isPending ||
                accounts.isPending ||
                accounts.isError
              }
            >
              {t("game.players.create")}
            </Button>
          </DialogActions>
        </Form>
      )}
    </Dialog>
  );
}
