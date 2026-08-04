#!/usr/bin/env python3
from __future__ import annotations

import build_batch05 as batch

# Close one deferred mathematics slot and one curated electronics/manual slot.
batch.CANDIDATES.insert(3, {
    "slot": 61,
    "title": "The First Six Books of the Elements of Euclid",
    "author": "Euclid and John Casey",
    "id": 21076,
})

# Catalog slot 90 explicitly calls for curated public-domain radio/electronics
# handbooks. This illustrated handbook is the first canonical selection.
batch.CANDIDATES.insert(15, {
    "slot": 90,
    "title": "The Radio Amateur's Hand Book",
    "author": "A. Frederick Collins",
    "id": 6935,
})

raise SystemExit(batch.main())
