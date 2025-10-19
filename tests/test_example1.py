# tests/test_example1.py
from pathlib import Path
import sys

# Rendre "src/" importable
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils import parse_any
from src.aba_core import ABA
from src.aba_attacks import compute_attacks_sets


def fset(xs):
    return frozenset(xs)


def test_aba_plus_example1_every_edge_is_both():
    """
    Avec PREF: alpha < beta, toutes les attaques doivent être 'both'.
    On ne regarde que les coalitions ∅, {alpha}, {beta}, {alpha,beta}.
    """
    p = ROOT / "data" / "example1.txt"
    raw = p.read_text(encoding="utf-8")
    data, _ = parse_any({"input": raw})

    aba = ABA.from_dict(data)
    args = aba.derive_arguments()
    atks = compute_attacks_sets(aba, args)

    keep = {fset([]), fset(["alpha"]), fset(["beta"]), fset(["alpha", "beta"])}

    # On ne garde que les arêtes entre coalitions d'intérêt
    filt = [t for t in atks if fset(t["X"]) in keep and fset(t["Y"]) in keep]
    # Chaque arête doit être 'both'
    not_both = [(t["X"], t["Y"], t.get("kind")) for t in filt if t.get("kind") != "both"]

    assert not not_both, (
        "Certaines arêtes ne sont pas 'both':\n" +
        "\n".join(f"{x} -> {y} (kind={k})" for x, y, k in not_both)
    )
