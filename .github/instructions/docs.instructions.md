---
applyTo: "docs/**,README.md"
---

# Documentation rules (ASD-STE100, Simplified Technical English)

All documentation is in English. The user interface is translated, but the documentation is not.

## Sentence rules
- Procedure sentence: maximum 20 words. Descriptive sentence: maximum 25 words.
- One instruction in each sentence. Start a step with a verb in the imperative: "Click Save."
- Use the active voice. Write "The system sends a message", not "A message is sent".
- Use the simple present tense for descriptions. Use the simple future only for real future events.
- Use articles ("the", "a", "an"). Do not omit them.
- Do not use contractions ("do not", not "don't").
- Keep a paragraph to a maximum of six sentences. Put one topic in each paragraph.
- Put a warning or a caution BEFORE the step it applies to.

## Word rules
- Use one word for one meaning. Use the same word for the same thing in all documents.
- Prefer simple verbs: "use" (not "utilize"), "start" (not "initiate"), "show" (not "display" when both are correct), "make sure" (not "ensure").
- Do not use idioms, slang, or phrasal verbs when a single verb works ("remove", not "take out").
- Do not use a noun cluster of more than three nouns. Rewrite with a preposition.
- Write numbers as digits. Write units with a space ("5 s", "90 %").
- Use the approved terms below. Add new terms to docs/developer/glossary.md before you use them.

| Term | Meaning | Do not use |
|---|---|---|
| exercise | one task: image and/or audio with a description | task, lesson, assignment |
| manager | user role with full rights | admin, teacher |
| student | user role that can only listen | pupil, child |
| listening session | one period of playback by a student | play event, view |
| journal | list of listening sessions | log, history |
| score | notes drawn from MusicXML | sheet, notation |
| original image | the uploaded picture of the notes | source picture |
| emergency manager | manager user defined in the .env file | backup admin, root user |

## Structure
- User documents (`docs/user/`): separate files for `manager.md` and `student.md`. Use numbered steps. After a step, say what the user sees ("The exercise list opens.").
- Developer documents (`docs/developer/`): `architecture.md`, `data-model.md`, `api.md`, `env-variables.md`, `deploy.md`, `ci-cd.md`, `omr-pipeline.md`, `spoken-notes.md`, `pwa-share.md`, `adding-a-language.md`, `troubleshooting.md`, `glossary.md`.
- Each document starts with a one-sentence purpose and a list of prerequisites.
- Code, commands, file names, and variable names use code formatting. They are not part of the sentence count.

## Check before you finish
1. No sentence is longer than the limit.
2. Every step starts with a verb.
3. No passive voice, no contractions, no idioms.
4. Terms match the table.
5. Every new feature is described in the user documents AND the developer documents.
