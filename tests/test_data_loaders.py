from __future__ import annotations

from pathlib import Path

from recllm_fairness.data.lastfm import load_lastfm
from recllm_fairness.data.movielens import load_movielens
from recllm_fairness.data.provenance import md5_checksum, verify_checksum


def test_movielens_25m_loader_computes_rank_tier_and_year(tmp_path: Path) -> None:
    (tmp_path / "movies.csv").write_text(
        "movieId,title,genres\n1,Toy Film (2001),Comedy|Drama\n2,Old Film (1999),Action\n"
        "3,Quiet Film,(no genres listed)\n",
        encoding="utf-8",
    )
    (tmp_path / "ratings.csv").write_text(
        "userId,movieId,rating,timestamp\n1,1,4,0\n2,1,5,0\n1,2,3,0\n1,3,3,0\n",
        encoding="utf-8",
    )
    items = load_movielens(tmp_path, "25m", head_quantile=0.34, mid_quantile=0.67)
    assert [item.item_id for item in items] == ["1", "2", "3"]
    assert items[0].popularity_rank == 1
    assert items[0].popularity_tier == "head"
    assert items[0].release_year == 2001
    assert items[0].genres == ["Comedy", "Drama"]
    assert items[2].genres == []


def test_lastfm_1k_loader_aggregates_events_to_artist(tmp_path: Path) -> None:
    path = tmp_path / "userid-timestamp-artid-artname-traid-traname.tsv"
    path.write_text(
        "u1\t2009-01-01\ta1\tArtist One\tt1\tTrack A\n"
        "u1\t2009-01-02\ta1\tArtist One\tt2\tTrack B\n"
        "u2\t2009-01-03\t\tArtist Two\tt3\tTrack C\n",
        encoding="utf-8",
    )
    items = load_lastfm(tmp_path, "1k", head_quantile=0.51, mid_quantile=0.76)
    assert len(items) == 2
    assert items[0].title == "Artist One"
    assert items[0].popularity_rank == 1
    assert items[1].item_id.startswith("name:")


def test_checksum_verification_is_streaming_and_strict(tmp_path: Path) -> None:
    archive = tmp_path / "sample.bin"
    archive.write_bytes(b"research-data")
    expected = "7930e1917f6a8150fb88abfe7b94eb19"
    assert md5_checksum(archive) == expected
    verify_checksum(archive, expected)
