# Dataset sources and provenance

The raw archives are intentionally excluded from version control. Download only from the
stable publisher/archive URLs below and verify the archive before extraction. The loaders
also support verifying a supplied archive with `verify_checksum`.

## MovieLens

Publisher: GroupLens Research, University of Minnesota.

| Use | Release | URL | Published MD5 |
|---|---|---|---|
| Pilot | MovieLens 1M | https://files.grouplens.org/datasets/movielens/ml-1m.zip | `c4d9eecfca2ab87c1945afe126590906` |
| Full | MovieLens 25M, December 2019 | https://files.grouplens.org/datasets/movielens/ml-25m.zip | `6b51fb2759a8657d3bfcbfc42b592ada` |

Official checksum files are available by appending `.md5` to each archive URL. The 25M
release contains 25,000,095 ratings and 62,423 movies. The 1M release contains 1,000,209
ratings and 3,883 movies.

License/use notes: MovieLens datasets may be used for research subject to the terms in each
archive README. They must not be redistributed without permission, used commercially, or
used to identify users. Cite Harper and Konstan (2015), *The MovieLens Datasets: History
and Context*, ACM TIIS, https://doi.org/10.1145/2827872.

## LastFM

Creator: Òscar Celma, Music Technology Group, Universitat Pompeu Fabra. The stable archival
record is Zenodo version 1.2: https://doi.org/10.5281/zenodo.6090214.

| Use | Release | URL | Archive MD5 |
|---|---|---|---|
| Pilot | LastFM-1K, May 2010 | https://zenodo.org/records/6090214/files/lastfm-dataset-1K.tar.gz | `a79a6808f54f73354789a9fb02cb1e41` |
| Full | LastFM-360K v1.2, March 2010 | https://zenodo.org/records/6090214/files/lastfm-dataset-360K.tar.gz | `635e6ed3fc873aa4ba33aba0ebce02b1` |

Important extracted-file checksums reported by the creator:

- 1K event file: `64747b21563e3d2aa95751e0ddc46b68`
- 1K profile file: `c53608b6b445db201098c1489ea497df`
- 360K interaction file: `be672526eb7c69495c27ad27803148f1`
- 360K profile file: `51159d4edf6a92cb96f87768aa2be678`

License/use notes: distributed with permission of Last.fm for **non-commercial use**.
Commercial users must contact Last.fm. The requested citation is Celma (2010), *Music
Recommendation and Discovery in the Long Tail*, Springer, and the Last.fm website.

## Operationalization notes

- Movie popularity is the number of ratings per movie, ranked descending with deterministic
  item-ID tie breaking.
- Music popularity is total play/listen count per artist. LastFM-1K track events are
  aggregated to artist level to match LastFM-360K's native user-artist-play schema.
- Popularity tiers are item-count quantiles (head/mid/tail), not interaction-mass quantiles.
  Cutoffs are recorded in `config/datasets.yaml` and every processed catalog row retains its
  rank and tier.
- LastFM does not supply reliable artist genre/provider/release-year metadata. These fields
  remain empty rather than being inferred from an undocumented external source.

