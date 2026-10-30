"""
Generate submission JSONL for VerifiedCart evaluation.
Usage:
  py generate_submission.py              # test set -> submission/R3_predictions.jsonl
  py generate_submission.py --mode dev   # dev set  -> submission/R3_predictions_dev.jsonl
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.stdout.reconfigure(encoding='utf-8')

import json
import pandas as pd
from engine.assistant import VerifiedCartEngine

def main():
    mode = "test"
    if "--mode" in sys.argv:
        idx = sys.argv.index("--mode")
        if idx + 1 < len(sys.argv):
            mode = sys.argv[idx + 1]

    print(f"=== VerifiedCart Submission Generator ===")
    print(f"Mode: {mode}")

    if mode == "dev":
        qfile = Path("data/questions_dev.csv")
        outfile = Path("submission/R3_predictions_dev.jsonl")
    else:
        qfile = Path("data/questions_test.csv")
        outfile = Path("submission/R3_predictions.jsonl")

    df = pd.read_csv(qfile, dtype=str)
    outfile.parent.mkdir(exist_ok=True)

    bot = VerifiedCartEngine()
    print(f"Processing {len(df)} questions...")

    # Group by conversation to handle multi-turn in order
    results = []
    conv_groups = {}
    for _, row in df.iterrows():
        cid = row["conversation_id"]
        if cid not in conv_groups:
            conv_groups[cid] = []
        conv_groups[cid].append(row)

    for cid in sorted(conv_groups.keys()):
        turns = sorted(conv_groups[cid], key=lambda r: int(r["turn"]))
        bot.reset_session(cid)
        for row in turns:
            qid = row["question_id"]
            query = row["question_text"]
            try:
                resp = bot.process(query, session_id=cid, question_id=qid)
                entry = {
                    "question_id": qid,
                    "action": resp["action"],
                    "answer_text": resp["answer_text"],
                    "cited_product_ids": resp["cited_product_ids"],
                    "cited_policy_sections": resp["cited_policy_sections"],
                    "stated_prices": resp["stated_prices"],
                    "stated_facts": resp.get("stated_facts", []),
                    "latency_ms": resp["latency_ms"],
                    "tokens_in": int(resp["tokens_in"]),
                    "tokens_out": int(resp["tokens_out"]),
                }
                results.append(entry)
                print(f"  [{qid}] {query[:42]:<42} -> {resp['action']:7s} (cited: {len(resp['cited_product_ids'])}p, {len(resp['cited_policy_sections'])}pol)")
            except Exception as e:
                print(f"  [{qid}] ERROR: {e}")
                results.append({
                    "question_id": qid,
                    "action": "refuse",
                    "answer_text": "I don't have that in our catalogue.",
                    "cited_product_ids": [],
                    "cited_policy_sections": [],
                    "stated_prices": [],
                    "stated_facts": [],
                    "latency_ms": 0,
                    "tokens_in": 0,
                    "tokens_out": 0,
                })

    with open(outfile, "w", encoding="utf-8") as f:
        for entry in results:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"\nDone! Written {len(results)} entries to {outfile}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
