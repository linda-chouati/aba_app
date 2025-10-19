
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils import parse_any
from src.aba_core import ABA
from src.aba_attacks import compute_attacks_sets


def fset(xs):
    return frozenset(xs)


def test_exos4_counts_match_prof():
    """
    Exo du prof (data/exos4.txt) avec PREF: a > b.
    On vérifie 12 attaques normales et 8 reverse.
    'both' compte dans les deux catégories (comme dans l'énoncé).
    """
    p = ROOT / "data" / "exos4.txt"
    assert p.exists(), f"Fichier manquant: {p}"

    raw = p.read_text(encoding="utf-8")
    data, _ = parse_any({"input": raw})

    aba = ABA.from_dict(data)
    args = aba.derive_arguments()

    atks_sets = compute_attacks_sets(aba, args)
    assert isinstance(atks_sets, list) and atks_sets, "Aucune attaque par coalitions trouvée"

    normals = [t for t in atks_sets if t.get("kind") in ("normal", "both")]
    reverses = [t for t in atks_sets if t.get("kind") in ("reverse", "both")]

    assert len(normals) == 12, f"Normales: attendu 12, obtenu {len(normals)}"
    assert len(reverses) == 8, f"Reverse: attendu 8, obtenu {len(reverses)}"


def test_exos4_includes_some_key_edges():
    """
    Vérifie quelques arêtes clés (sous-ensemble) de la correction.
    """
    p = ROOT / "data" / "exos4.txt"
    raw = p.read_text(encoding="utf-8")
    data, _ = parse_any({"input": raw})

    aba = ABA.from_dict(data)
    args = aba.derive_arguments()
    atks_sets = compute_attacks_sets(aba, args)

    normals = {(fset(t["X"]), fset(t["Y"])) for t in atks_sets if t.get("kind") in ("normal", "both")}
    reverses = {(fset(t["X"]), fset(t["Y"])) for t in atks_sets if t.get("kind") in ("reverse", "both")}

    expected_normals = {
        (fset(["a","c"]), fset(["b"])),
        (fset(["a","c"]), fset(["c"])),
        (fset(["a","c"]), fset(["a","b"])),
        (fset(["a","b","c"]), fset(["b"])),
        (fset(["a","b","c"]), fset(["c"])),
        (fset(["a","b","c"]), fset(["a","b"])),
    }
    expected_reverses = {
        (fset(["a"]), fset(["b","c"])),
        (fset(["a"]), fset(["a","b","c"])),
        (fset(["a","b"]), fset(["b","c"])),
        (fset(["a","b"]), fset(["a","b","c"])),
        (fset(["a","c"]), fset(["b","c"])),
        (fset(["a","c"]), fset(["a","b","c"])),
        (fset(["a","b","c"]), fset(["b","c"])),
        (fset(["a","b","c"]), fset(["a","b","c"])),
    }

    assert expected_normals.issubset(normals), f"Arêtes normales manquantes: {sorted(expected_normals - normals)}"
    assert expected_reverses.issubset(reverses), f"Arêtes reverse manquantes: {sorted(expected_reverses - reverses)}"
