# Solfège Trainer: Copilot kit

Copy the contents of this archive into the ROOT of your repository (keep the folder structure).

```
.github/
  copilot-instructions.md            <- read automatically in every Copilot session
  instructions/
    backend.instructions.md          <- applies to backend/** and worker/**
    frontend.instructions.md         <- applies to frontend/**
    docs.instructions.md             <- applies to docs/** (ASD-STE100 rules)
docs/
  PRODUCT_BRIEF.md                   <- full requirements
  PHASES.md                          <- phase plan (0.5 to 7)
  STATUS.md                          <- living state file (Copilot updates it)
  DECISIONS.md                       <- decision log
```

## How to start

1. Commit these files to the `main` branch.
2. Start a new Copilot chat and send:

```
Read .github/copilot-instructions.md, docs/PRODUCT_BRIEF.md, docs/PHASES.md and docs/STATUS.md.
We start PHASE 0.5. Do not write code yet. Give me a task checklist, assumptions, and open questions.
```

3. Approve the plan. Then send one task at a time:

```
Execute task 1 from the plan. Failing tests first. Run checks. Commit. Stop.
```

## To continue after a break

```
Read docs/STATUS.md and the current git log. Continue PHASE N from the first unchecked task.
Failing tests first. Commit when checks are green. Stop after this task.
```

## If the model breaks a rule

```
Stop. You broke a rule from the brief: <rule>. Revert the last change, restate the rules that apply
to this task in your own words, then redo the task.
```

Note: put your 5-10 real exercise images in `prototypes/omr/samples/` before PHASE 0.5.
