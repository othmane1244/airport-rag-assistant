# Generation evaluation protocol

The retrieval benchmark (`rag_service/evaluation`) measures whether an expected source is
*retrieved*. This folder measures what the user actually reads: the **generated answer** returned
by `POST /chat`. Answers are rated **by hand**; no score in this folder is produced by a model.

## 1. Sample

`select_questions.py` draws 40 questions from `benchmark_v2_150.json` with a fixed seed
(`20261108`) and writes `questions_40.json`.

| | fr | en | ar | total |
|---|---|---|---|---|
| Answerable | 10 | 10 | 10 | 30 |
| Unanswerable (no answer in the corpus) | 3 | 3 | 4 | 10 |

Answerable questions are stratified by category in proportion to the benchmark, per language:
transport 3, services 3, medical 1, accessibility 1, airport_info 1, formalites 1.
Ten of the 40 (7 answerable, 3 unanswerable) are flagged `double_annotation` for the
inter-annotator agreement check.

Limits of the sample: 40 questions is small (a 95 % confidence interval on a proportion measured
on 30 answers is roughly ±15 points), the questions were written by the author, and the benchmark has
not been reviewed by an airport-domain expert.

## 2. Collecting answers

1. Start the stack with authentication bypassed **for local evaluation only**:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.eval.yml up -d
   ```
   `docker-compose.eval.yml` sets `ENVIRONMENT=development` and `AUTH_DISABLED=true`. The API only
   honours the bypass in development mode. Alternatively, pass a Keycloak access token with
   `--token` (or `AGA_TOKEN`) against the normal stack.
2. Check that `GET /ready` returns 200 and that the `aga_documents` collection is not empty.
3. Run:
   ```bash
   python eval/run_generation.py
   ```
   It waits 2.5 s between requests (the API allows 30 chat requests per minute per account) and
   writes `results/answers-<UTC timestamp>.csv` with: id, language, category, question, reply,
   returned sources, **engine**, HTTP status, client-side latency.

### The `engine` field

On this branch `/chat` returns which component produced the answer:

| engine | meaning |
|---|---|
| `gemini` | Gemini wrote the answer |
| `groq` | Gemini failed, Groq wrote the answer |
| `fallback_parking` | both LLMs failed; hard-coded parking answer (triggered by the parking source text) |
| `fallback_excerpt` | both LLMs failed; raw excerpt of the first retrieved passage |
| `fallback_unavailable` | both LLMs failed and no excerpt was available |
| `no_result` | no passage left after retrieval and topic filtering; fixed abstention message |
| `out_of_scope` | intent router answered "out of scope" without retrieval |
| `flight_redirect` | intent router redirected to the official ONDA flight search |
| `greeting` | intent router answered a greeting |

Answers not written by an LLM must be analysed separately: a fixed message or a hard-coded answer
says nothing about generation quality.

## 3. Annotation

`make_grid.py results/answers-<ts>.csv` creates two Excel files with empty rating columns and
drop-down lists:

- `answers-<ts>-grid-A.xlsx`: all 40 answers (main annotator);
- `answers-<ts>-grid-B.xlsx`: the 10 double-annotation answers (second annotator, who must not see
  grid A).

Greyed cells do not apply to that row and are ignored by the scoring script.

**The answers and grids are regenerated locally and are not committed.** `eval/results/` is ignored by
Git: generated answers quote the source documents (including third-party contact details), and the
`.xlsx` grids are office files. Run `run_generation.py`, then `make_grid.py`, to rebuild them on your
own machine.

| Column | Applies to | Values | Rule |
|---|---|---|---|
| `exactitude` | answerable | exacte / partielle / fausse | **exacte**: every fact the question needs is present and correct. **partielle**: correct but incomplete, or correct with a minor error that would not mislead. **fausse**: a wrong fact that could mislead a passenger, or no useful answer to an answerable question (including an unjustified abstention). |
| `fidele_source` | answerable | oui / non | **oui** if every factual claim in the answer is supported by the cited source documents. Check the PDF if needed. An answer can be *exacte* but not faithful (correct fact, not in the source). |
| `bonne_langue` | all | oui / non | **oui** if the whole answer is in the question's language (proper nouns and document titles excepted). |
| `abstention_correcte` | unanswerable | oui / non | **oui** if the assistant says it cannot answer reliably and/or redirects to an official source, **without** inventing a specific fact (time, price, flight status…). |
| `commentaire` | all | free text | Required when the rating is *partielle*, *fausse* or *non*: say what is wrong. |

Annotate each row independently, from the question, the answer and the sources only. Do not change a
rating after seeing the scores.

## 4. Scoring

```bash
python eval/score.py results/answers-<ts>-grid-A.xlsx [results/answers-<ts>-grid-B.xlsx]
```

Outputs, saved as `<grid>-scores.json`:

- answerable questions: share of *exacte / partielle / fausse*, share faithful to the source,
  share in the right language;
- unanswerable questions: share of correct abstentions, share in the right language;
- the same figures by language and by engine;
- with grid B: raw agreement and Cohen's kappa per criterion on the 10 shared answers (kappa is
  reported as `null` when both annotators used one identical label, where it is undefined).

Empty cells are counted as *not rated* and excluded from percentages; the report shows how many.

## 5. Requirements

```bash
pip install -r eval/requirements.txt   # requests, openpyxl
```

## 6. Run findings (2026-11-08)

One run was made on 2026-11-08 against the Compose stack with `docker-compose.eval.yml`. Its answers
file and annotation grids are **not published** (see above), so the figures from that run are not
reproduced here. Qualitative findings, kept to explain the design choices that followed; **none was
fixed on that branch**, on purpose, so that annotation describes the system as it was:

1. **Two LLMs in practice.** The Gemini key was on the free tier, which caps `gemini-2.5-flash`
   requests per day (`GenerateRequestsPerDayPerProjectPerModel-FreeTier`, HTTP 429 once exceeded).
   After that, questions went to Groq, so the results mix two models and Groq acts as a co-primary
   provider rather than an occasional fallback.
2. **Answerable questions that never reached the model.** Some were wrongly classified out of scope
   by the keyword router (`fr_rental_contacts`, `ar_wheelchair`); others were emptied by the topic
   filter (`_TOPIC_SOURCE_RULES`): for `en_bus_route` and `ar_bus_route` the "bus" rule kept only the
   Taxi & Bus page, which was not among the retrieved candidates, so the user got the fixed
   "no document found" message.
3. **Truncated answer.** For `fr_travel_customs`, Gemini returned 429 and Groq's answer was truncated
   at the output token limit; the API rejects truncated answers, so the user received the raw excerpt
   of the first retrieved passage.
