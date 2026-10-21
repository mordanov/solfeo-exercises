# Solfège Trainer

This glossary defines product terms for exercises, student listening, and the note game.

## Exercise organization

**Chapter**:
A numbered group of exercises that a manager creates and a student can select with other chapters for a listening run. Each exercise belongs to exactly one chapter.
_Avoid_: Category, level
<!-- source: docs/developer/glossary.md:10 -->

**Listening run**:
One active selection of chapters and up to 10 exercises, sampled and shuffled once, that a student can resume across devices or cancel.
_Avoid_: Exercise, listening session
<!-- source: docs/developer/glossary.md:11 -->

## Guess the Note

**Clef mode**:
The selection of treble only, bass only, or both clefs before a round. Both is the default.
Mixed rounds use a randomized 3-and-4 split. The selection does not change scoring.
_Avoid_: Difficulty, note naming
<!-- source: backend/app/game/services/rounds.py:90-126; frontend/src/features/game/notes.ts:14-25 -->
