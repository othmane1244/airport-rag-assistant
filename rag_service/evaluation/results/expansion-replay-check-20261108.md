# Query expansion: replay check of the 2026-10-10 benchmark runs

Date: 2026-11-08. Live `rag` container whose `app/routers/query.py` is identical to the repository.
Index `aga_documents`: 15,346 passages (15,347 on 2026-10-10). Audience `voyageur`, top 3 cosine
distances shown.

## Code paths

- `rag_service/app/routers/query.py:91`: `retrieval_query = _expand_domain_query(request.query)`.
  Every `POST /query` is expanded by the service.
- `rag_service/scripts/evaluate_retrieval.py:102-108`: with `--query-expansion` the script applies
  `_expand_domain_query` **before** sending; without it, it sends the raw question. In both cases the
  service then expands again.

So the archived "baseline" run = expansion applied once (by the service), and the "expanded" run =
expansion applied twice (script + service; the anchor phrase is appended twice).

## Replay (distances)

| id | no expansion at all (Chroma queried directly) | archived "baseline" | live `/query` with raw question | archived "expanded" | live `/query` with the string the "expanded" run sent |
|---|---|---|---|---|---|
| fr_parking | 0.7343, 0.8440, 0.8519 | 0.5599, 0.6113, 0.6393 | 0.5599, 0.6113, 0.6393 | 0.5990, 0.6284, 0.6652 | 0.5990, 0.6284, 0.6724 |
| ar_parking_info | 0.8761, 1.1160, 1.1219 | 0.5364, 0.7187, 0.7291 | 0.5364, 0.7187, 0.7444 | 0.5296, 0.6968, 0.6992 | 0.5296, 0.6968, 0.6992 |
| ar_iata | 0.9396, 0.9413, 0.9634 | 0.6814, 0.6855, 0.7092 | 0.6814, 0.6855, 0.6962 | 0.6997, 0.7113, 0.7181 | 0.6907, 0.6997, 0.7113 |
| en_taxi (not expanded) | – | 0.8834, 0.8924, 1.0622 | 0.8834, 0.8924, 1.0622 | 0.8834, 0.8924, 1.0622 | 0.8834, 0.8924, 1.0622 |
| fr_wifi (not expanded) | – | 0.6304, 0.7935, 0.7943 | 0.6304, 0.7935, 0.7943 | 0.6304, 0.7935, 0.7943 | 0.6304, 0.7935, 0.7943 |

The archived "baseline" distances are reproduced by the live service (which expands), and are far
from the distances of a truly unexpanded query. Small differences at rank 3 are consistent with the
one-passage change in the index.

## Conclusion

Both archived runs include the expansion. Their comparison does not isolate its effect. The 92.5 %
Hit@3 is valid for the complete system, expansion included. Measuring the expansion requires a
switch to disable it in the service.
