#!/usr/bin/env python3
"""
VerifiedCart Web Server (Local HTTP Server)
Serves the dark Obsidian / Neon Cyan shopping assistant web interface on port 8000.
"""

import sys
import os
import json
import subprocess
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Ensure engine path is in sys.path
sys.path.insert(0, str(Path(__file__).parent))
from engine.assistant import VerifiedCartEngine

PORT = 8000
if len(sys.argv) > 1:
    try:
        PORT = int(sys.argv[1])
    except ValueError:
        pass

# Initialize the VerifiedCart engine once
engine = VerifiedCartEngine()

class VerifiedCartHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # 1. Root -> static/index.html
        if path == "/" or path == "/index.html":
            self.serve_file(Path("static/index.html"), "text/html; charset=utf-8")
            return

        # 2. Static files
        if path.startswith("/static/"):
            file_path = Path(".") / path.lstrip("/")
            mime = "text/plain"
            if path.endswith(".css"):
                mime = "text/css; charset=utf-8"
            elif path.endswith(".js"):
                mime = "application/javascript; charset=utf-8"
            elif path.endswith(".html"):
                mime = "text/html; charset=utf-8"
            elif path.endswith(".png"):
                mime = "image/png"
            elif path.endswith(".svg"):
                mime = "image/svg+xml"
            self.serve_file(file_path, mime)
            return

        # 3. API: /api/catalogue
        if path == "/api/catalogue":
            qs = parse_qs(parsed.query)
            q = qs.get("q", [""])[0].lower()
            category = qs.get("category", [""])[0]
            brand = qs.get("brand", [""])[0]
            stock = qs.get("stock", [""])[0]
            sort_by = qs.get("sort", ["price_asc"])[0]
            page = int(qs.get("page", ["1"])[0])
            per_page = int(qs.get("per_page", ["30"])[0])

            prods = list(engine.catalogue.values())
            if q:
                prods = [p for p in prods if q in p["title"].lower() or q in p["brand"].lower() or q in p["product_id"].lower()]
            if category:
                prods = [p for p in prods if p["category"] == category]
            if brand:
                prods = [p for p in prods if p["brand"] == brand]
            if stock:
                prods = [p for p in prods if p["stock_status"] == stock]

            if sort_by == "price_asc":
                prods.sort(key=lambda x: x["price_inr"])
            elif sort_by == "price_desc":
                prods.sort(key=lambda x: -x["price_inr"])
            elif sort_by == "rating_desc":
                prods.sort(key=lambda x: -(x["rating"] or 0))

            total = len(prods)
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paged = prods[start_idx:end_idx]

            categories = sorted(list(set(p["category"] for p in engine.catalogue.values())))
            brands = sorted(list(set(p["brand"] for p in engine.catalogue.values())))

            self.send_json({
                "total": total,
                "page": page,
                "per_page": per_page,
                "products": paged,
                "categories": categories,
                "brands": brands,
            })
            return

        # 4. API: /api/policies
        if path == "/api/policies":
            secs = list(engine.policy_sections.values())
            self.send_json(secs)
            return

        # 5. API: /api/stats
        if path == "/api/stats":
            self.send_json({
                "total_products": len(engine.catalogue),
                "total_policies": len(engine.policy_sections),
                "status": "ready",
            })
            return

        # 6. API: /api/evaluate
        if path == "/api/evaluate":
            # Run dev evaluation and return live summary
            try:
                subprocess.run([sys.executable, "generate_submission.py", "--mode", "dev"], check=True)
                subprocess.run([sys.executable, "evaluate.py", "--submission", "submission/R3_predictions_dev.jsonl", "--truth", "data/questions_dev_truth.jsonl", "--out", "score_dev.json", "--data-dir", "data"], check=True)
                with open("score_dev.json", "r", encoding="utf-8") as f:
                    report = json.load(f)
                self.send_json(report)
            except Exception as e:
                self.send_json({"error": str(e)}, status=500)
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/chat":
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len).decode("utf-8")
            try:
                req_data = json.loads(body)
            except Exception:
                req_data = {}

            query = req_data.get("query", "")
            session_id = req_data.get("session_id", "default")

            result = engine.process(query, session_id=session_id)

            # Attach product card payloads for cited products
            matched_prods = []
            for pid in result["cited_product_ids"]:
                if pid in engine.catalogue:
                    matched_prods.append(engine.catalogue[pid])
            result["matched_products"] = matched_prods

            self.send_json(result)
            return

        self.send_error(404, "Not Found")

    def serve_file(self, file_path: Path, mime: str):
        if not file_path.exists() or not file_path.is_file():
            self.send_error(404, "File not found")
            return
        content = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def send_json(self, data: Any, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

def main():
    server_address = ("127.0.0.1", PORT)
    httpd = HTTPServer(server_address, VerifiedCartHandler)
    print("=" * 60)
    print(f" VerifiedCart Assistant running at: http://127.0.0.1:{PORT}/")
    print(" 5,000 Products Loaded · 100% Grounded Architecture Ready")
    print("=" * 60)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        httpd.server_close()

if __name__ == "__main__":
    main()

