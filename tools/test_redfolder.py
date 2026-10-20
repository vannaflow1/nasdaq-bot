import sys, os, json; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import redfolder; os.makedirs("knowledge/research_out", exist_ok=True)
w = redfolder.week(); f = redfolder.today_flags()
open("knowledge/research_out/test_redfolder.txt", "w").write(f"{len(w)} events this week; high USD: " + json.dumps([e for e in w if e.get('impact') == 'High' and e.get('country') == 'USD'][:12]) + "\nTODAY: " + json.dumps(f))
