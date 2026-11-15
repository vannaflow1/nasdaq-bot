import json, os, unittest
from _util import ROOT
import families as F, sealed
import ledger_check as LC

K = os.path.join(ROOT, "knowledge")


class Integrity(unittest.TestCase):
    def test_ledgers_and_frozen_files_match_the_last_checkpoint(self):
        cur, errs, chain = LC.check()                              # read-only: does not move the checkpoint
        self.assertEqual(errs, [], "a frozen file or append-only ledger was changed")

    def test_every_registered_family_still_matches_its_frozen_fingerprint(self):
        fams = json.load(open(os.path.join(K, "families.json")))
        self.assertGreaterEqual(len(fams), 15)
        for f in fams:
            if f.get("hash"): self.assertEqual(F.fam_hash(f), f["hash"], f"{f['id']}: rules or grid changed after registration")

    def test_no_family_has_more_than_50_variants_and_variants_are_reproducible(self):
        for f in json.load(open(os.path.join(K, "families.json"))):
            v = F.variants(f)
            self.assertLessEqual(len(v), 50, f["id"])
            self.assertEqual(json.dumps(v, sort_keys=True), json.dumps(F.variants(f), sort_keys=True), f["id"])

    def test_alpha_budget_numbers(self):
        self.assertEqual([round(sealed.alpha_v2(j), 4) for j in (1, 2, 3)], [0.0304, 0.0076, 0.0034])   # 0.05*6/(pi^2 j^2)
        self.assertEqual([round(sealed.alpha_v2(j), 4) for j in (4, 5, 6)], [0.0040, 0.0023, 0.0023])   # fixed slots
        self.assertEqual(sealed.alpha_v2(7), 0.0)                                                      # then no more families
        self.assertEqual([sealed.alpha_fast(j) for j in range(1, 7)], [0.01] * 5 + [0.0])               # fast epoch: 5 slots


if __name__ == "__main__":
    unittest.main()
