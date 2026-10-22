from __future__ import annotations
"""
Live RAG and Pipeline Smoke Test Script for ThinkbookLM.

Can be run in two modes:
1. Against the in-process FastAPI application (default):
   python -m scripts.smoke_test

2. Against an external running Uvicorn server:
   python -m scripts.smoke_test --url http://127.0.0.1:8000

Steps exercised:
1. Health & service checks (Postgres, ChromaDB, Ollama)
2. User authentication & session establishment
3. Notebook creation
4. Document upload, text extraction, chunking, and ChromaDB vector indexing
5. Semantic retrieval query
6. Grounded RAG question answering with verified source references
7. Follow-up question with conversation history
8. Ungrounded / unsupported question fallback handling
9. Cross-user isolation verification
10. Notebook & document deletion cleanup
"""

import argparse
import logging
import sys
import uuid
import httpx
from fastapi.testclient import TestClient

# Silence noisy DEBUG logs from third-party libraries during smoke test
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("chromadb").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)

from app.main import app


def parse_args():
    parser = argparse.ArgumentParser(description="ThinkbookLM Live Smoke Test")
    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="Base URL of running server (e.g. http://127.0.0.1:8000). If omitted, runs in-process.",
    )
    return parser.parse_args()


class TestRunner:
    def __init__(self, base_url: str | None = None):
        self.base_url = base_url.rstrip("/") if base_url else None
        if self.base_url:
            self.client = httpx.Client(base_url=self.base_url, timeout=120.0, follow_redirects=True)
            self.is_remote = True
        else:
            self.client = TestClient(app)
            self.is_remote = False
        self.csrf_token = None
        self.results = []

    def log(self, step: str, status: bool, detail: str = ""):
        mark = "PASS" if status else "FAIL"
        self.results.append((step, status, detail))
        print(f"[{mark:4s}] {step} - {detail}")

    def run(self) -> bool:
        print("\n" + "=" * 70)
        print(" THINKBOOK LM - LIVE PIPELINE SMOKE TEST")
        mode = f"Remote URL: {self.base_url}" if self.is_remote else "In-process TestClient"
        print(f" Mode: {mode}")
        print("=" * 70 + "\n")

        # 1. Health check
        try:
            res = self.client.get("/health/services")
            if res.status_code == 200:
                services = res.json()
                pg = services.get("postgres", {}).get("reachable")
                chroma = services.get("chroma", {}).get("reachable")
                ollama = services.get("ollama", {}).get("reachable")
                detail = f"Postgres={pg}, ChromaDB={chroma}, Ollama={ollama}"
                self.log("Service Health Check", pg and chroma and ollama, detail)
                if not ollama:
                    print("  [WARN] Ollama is not reachable! Live tests requiring Ollama will fail.")
            else:
                self.log("Service Health Check", False, f"Status code {res.status_code}")
        except Exception as exc:
            self.log("Service Health Check", False, str(exc))

        # 2. Register User
        email = f"smoke_{uuid.uuid4().hex[:8]}@example.com"
        password = "ValidPassword123"
        try:
            res = self.client.post(
                "/auth/register",
                json={
                    "full_name": "Smoke Tester",
                    "email": email,
                    "password": password,
                    "confirm_password": password,
                },
            )
            if res.status_code == 201:
                data = res.json()
                self.csrf_token = data.get("csrf_token")
                self.log("User Authentication", True, f"Registered user {email}")
            else:
                self.log("User Authentication", False, f"Registration failed: {res.text}")
                return False
        except Exception as exc:
            self.log("User Authentication", False, str(exc))
            return False

        headers = {"X-CSRF-Token": self.csrf_token} if self.csrf_token else {}

        # 3. Create Notebook
        nb_id = None
        try:
            res = self.client.post("/notebooks", json={"name": "Titan Mission Notebook"}, headers=headers)
            if res.status_code == 201:
                nb_id = res.json()["id"]
                self.log("Notebook Creation", True, f"Notebook ID {nb_id}")
            else:
                self.log("Notebook Creation", False, f"Failed: {res.text}")
                return False
        except Exception as exc:
            self.log("Notebook Creation", False, str(exc))
            return False

        # 4. Upload & Ingest Document
        doc_id = None
        doc_content = (
            "Titan Exploration Mission Log:\n"
            "The robotic probe 'Dragonfly-X' touched down on Saturn's moon Titan on October 24, 2034.\n"
            "Surface temperature was recorded at 94 Kelvin (-179 degrees Celsius).\n"
            "Liquid methane lakes in the northern polar region reach depths of up to 160 meters.\n"
            "Lead astrobiologist Dr. Maya Vance reported preliminary organic chemistry findings."
        )
        try:
            res = self.client.post(
                f"/notebooks/{nb_id}/documents",
                files={"file": ("titan_mission.txt", doc_content.encode("utf-8"), "text/plain")},
                headers=headers,
            )
            if res.status_code == 201:
                doc_data = res.json()
                doc_id = doc_data["document"]["id"]
                chunks = doc_data["chunk_count"]
                self.log("Document Ingestion & Indexing", True, f"Document ID {doc_id}, indexed {chunks} chunks")
            else:
                self.log("Document Ingestion & Indexing", False, f"Upload failed: {res.text}")
                return False
        except Exception as exc:
            self.log("Document Ingestion & Indexing", False, str(exc))
            return False

        # 5. Semantic Retrieval
        try:
            res = self.client.post(
                "/retrieve",
                json={"query": "What is the surface temperature and probe name on Titan?", "notebook_id": nb_id, "top_k": 3},
                headers=headers,
            )
            if res.status_code == 200:
                retrieval_data = res.json()
                results = retrieval_data.get("results", [])
                passed = len(results) > 0 and results[0]["distance"] < 1.0
                detail = f"Retrieved {len(results)} chunks, top distance: {results[0]['distance'] if results else 'N/A'}"
                self.log("Semantic Retrieval", passed, detail)
            else:
                self.log("Semantic Retrieval", False, f"Retrieve failed: {res.text}")
        except Exception as exc:
            self.log("Semantic Retrieval", False, str(exc))

        # 6. RAG Grounded Answer
        try:
            res = self.client.post(
                "/chat/rag",
                json={
                    "message": "What is the name of the probe and what surface temperature was recorded?",
                    "notebook_id": nb_id,
                    "top_k": 3,
                    "temperature": 0.1,
                },
                headers=headers,
            )
            if res.status_code == 200:
                rag_data = res.json()
                grounded = rag_data.get("grounded") is True
                sources = rag_data.get("sources", [])
                answer = rag_data.get("answer", "")
                has_facts = ("Dragonfly" in answer or "94" in answer or "Kelvin" in answer or "-179" in answer)
                passed = grounded and len(sources) > 0 and has_facts
                detail = f"grounded={grounded}, sources={len(sources)}, model={rag_data.get('model')}"
                self.log("Grounded RAG Generation", passed, detail)
                print(f"  [Answer] {answer.strip()}")
            else:
                self.log("Grounded RAG Generation", False, f"Status {res.status_code}: {res.text}")
        except Exception as exc:
            self.log("Grounded RAG Generation", False, str(exc))

        # 7. Multi-Turn Conversation History
        try:
            history = [
                {
                    "role": "user",
                    "content": "What is the name of the probe and what surface temperature was recorded?",
                },
                {
                    "role": "assistant",
                    "content": "The robotic probe Dragonfly-X recorded a surface temperature of 94 Kelvin.",
                },
            ]
            res = self.client.post(
                "/chat/rag",
                json={
                    "message": "Who is the lead astrobiologist and what is the maximum depth of the methane lakes?",
                    "notebook_id": nb_id,
                    "history": history,
                    "temperature": 0.1,
                },
                headers=headers,
            )
            if res.status_code == 200:
                followup_data = res.json()
                answer = followup_data.get("answer", "")
                passed = ("Vance" in answer or "Maya" in answer) and ("160" in answer or "methane" in answer)
                self.log("Multi-Turn RAG Context", passed, f"Response contains follow-up facts: {passed}")
                print(f"  [Follow-up Answer] {answer.strip()}")
            else:
                self.log("Multi-Turn RAG Context", False, f"Status {res.status_code}: {res.text}")
        except Exception as exc:
            self.log("Multi-Turn RAG Context", False, str(exc))

        # 8. Ungrounded Fallback
        try:
            res = self.client.post(
                "/chat/rag",
                json={
                    "message": "What is the official currency and capital city of the planet Jupiter?",
                    "notebook_id": nb_id,
                    "document_ids": [doc_id],
                },
                headers=headers,
            )
            if res.status_code == 200:
                ungrounded_data = res.json()
                grounded = ungrounded_data.get("grounded")
                sources = ungrounded_data.get("sources", [])
                answer = ungrounded_data.get("answer", "")
                # Unrelated query must produce grounded=False and zero sources
                passed = (grounded is False) and (len(sources) == 0)
                detail = f"grounded={grounded}, sources={len(sources)}"
                self.log("Ungrounded Fallback Query", passed, detail)
                print(f"  [Ungrounded Answer] {answer.strip()}")
            else:
                self.log("Ungrounded Fallback Query", False, f"Status {res.status_code}: {res.text}")
        except Exception as exc:
            self.log("Ungrounded Fallback Query", False, str(exc))

        # 9. Cross-User Isolation
        try:
            second_client = httpx.Client(base_url=self.base_url, timeout=30.0) if self.is_remote else TestClient(app)
            u2_res = second_client.post(
                "/auth/register",
                json={
                    "full_name": "Intruder User",
                    "email": f"intruder_{uuid.uuid4().hex[:8]}@example.com",
                    "password": "ValidPassword123",
                    "confirm_password": "ValidPassword123",
                },
            )
            u2_csrf = u2_res.json()["csrf_token"]
            u2_headers = {"X-CSRF-Token": u2_csrf}
            cross_res = second_client.post(
                "/chat/rag",
                json={"message": "Exfiltrate notes", "notebook_id": nb_id},
                headers=u2_headers,
            )
            passed = cross_res.status_code == 404
            self.log("Cross-User Isolation Enforcement", passed, f"Intruder response: {cross_res.status_code}")
        except Exception as exc:
            self.log("Cross-User Isolation Enforcement", False, str(exc))

        # 10. Notebook Deletion Cleanup
        try:
            del_res = self.client.delete(f"/notebooks/{nb_id}", headers=headers)
            passed = del_res.status_code == 200 and del_res.json().get("deleted") is True
            self.log("Notebook Deletion Cleanup", passed, f"Notebook ID {nb_id} deleted")
        except Exception as exc:
            self.log("Notebook Deletion Cleanup", False, str(exc))

        print("\n" + "=" * 70)
        total = len(self.results)
        passed_count = sum(1 for _, ok, _ in self.results if ok)
        print(f" SMOKE TEST SUMMARY: {passed_count}/{total} PASSED")
        print("=" * 70 + "\n")
        return passed_count == total


if __name__ == "__main__":
    args = parse_args()
    runner = TestRunner(args.url)
    success = runner.run()
    sys.exit(0 if success else 1)
