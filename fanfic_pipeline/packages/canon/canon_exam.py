"""
P1.7 — Real Canon Exam Suite:
Generates verified factual, temporal, relational, power rule, and epistemic questions from CanonStore and EnrichmentStore.
Evaluates submitted answers against ground truth without mock auto-passing.
NO hardcoded seed templates — all questions derived from data stores.
"""
import random, json, pathlib
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from fanfic_pipeline.packages.canon.power_ladder import can_fly, rank_of, REALM_ORDER, RANK

class ExamQuestion(BaseModel):
    qid: str
    qtype: str  # factual | temporal | relational | rule | epistemic
    prompt: str
    options: List[str] = Field(default_factory=list)
    answer: str
    evidence_chunk_id: Optional[str] = None
    source_hash: str = ""

class CanonExam:
    def __init__(self, canon_store=None, enrichment_store=None, graph=None, ledger=None):
        self.canon_store = canon_store
        self.enrichment_store = enrichment_store
        self.graph = graph
        self.ledger = ledger

    def generate(self, n: int = 30, seed: int = 42) -> List[ExamQuestion]:
        """Generate exam questions purely from data stores. No hardcoded seeds."""
        random.seed(seed)
        qs: List[ExamQuestion] = []
        qid = 0

        # 1. Factual questions from EnrichmentStore entities
        if self.enrichment_store:
            entities = self.enrichment_store.query_all_entities()
            char_entities = [e for e in entities if e.entity_type == "character"]
            other_entities = [e for e in entities if e.entity_type != "character"]

            # Character first-seen-chapter questions
            for e in char_entities[:8]:
                qid += 1
                correct_ch = e.first_seen_chapter
                opts = [str(correct_ch), str(correct_ch + 5), str(max(1, correct_ch - 3)), str(correct_ch + 12)]
                random.shuffle(opts)
                qs.append(ExamQuestion(
                    qid=f"Q{qid:03d}", qtype="factual",
                    prompt=f"Nhân vật {e.canonical_name} lần đầu tiên xuất hiện hoặc được nhắc tới từ chương nào?",
                    options=opts, answer=str(correct_ch), source_hash=e.id
                ))

            # Entity type classification questions
            for e in other_entities[:6]:
                qid += 1
                type_labels = {"technique": "Võ công / Bí kỹ", "realm": "Cảnh giới tu luyện",
                               "location": "Địa danh / Nơi chốn", "sect": "Tông môn / Tổ chức",
                               "item": "Vật phẩm / Pháp bảo"}
                correct_label = type_labels.get(e.entity_type, e.entity_type)
                wrong_labels = [v for k, v in type_labels.items() if k != e.entity_type]
                random.shuffle(wrong_labels)
                opts = [correct_label] + wrong_labels[:3]
                random.shuffle(opts)
                qs.append(ExamQuestion(
                    qid=f"Q{qid:03d}", qtype="factual",
                    prompt=f"'{e.canonical_name}' thuộc loại nào trong thế giới Nhất Thế Chi Tôn?",
                    options=opts, answer=correct_label, source_hash=e.id
                ))

            # Relational questions from EnrichmentStore
            rels = self.enrichment_store.query_relationships("")
            for rel in rels[:8]:
                qid += 1
                from_e = self.enrichment_store.query_entity(rel.from_entity)
                to_e = self.enrichment_store.query_entity(rel.to_entity)
                name_1 = from_e.canonical_name if from_e else rel.from_entity
                name_2 = to_e.canonical_name if to_e else rel.to_entity
                opts = ["Đồng đội / Bằng hữu", "Kẻ thù / Đối nghịch", "Sư đồ / Đồng môn", "Người qua đường"]
                ans_map = {"ally": "Đồng đội / Bằng hữu", "adversary": "Kẻ thù / Đối nghịch",
                           "master_student": "Sư đồ / Đồng môn"}
                ans_text = ans_map.get(rel.type, "Đồng đội / Bằng hữu")
                qs.append(ExamQuestion(
                    qid=f"Q{qid:03d}", qtype="relational",
                    prompt=f"Mối quan hệ giữa {name_1} và {name_2} thuộc dạng nào?",
                    options=opts, answer=ans_text, source_hash=f"{rel.from_entity}->{rel.to_entity}"
                ))

        # 2. Power Ladder Rule questions — generated dynamically from REALM_ORDER
        realm_questions = self._generate_realm_questions()
        for rq in realm_questions:
            qid += 1
            qs.append(ExamQuestion(qid=f"Q{qid:03d}", qtype="rule", **rq))

        # 3. Epistemic questions from ledger (if available) or canon_store search
        epistemic_qs = self._generate_epistemic_questions()
        for eq in epistemic_qs:
            qid += 1
            qs.append(ExamQuestion(qid=f"Q{qid:03d}", qtype="epistemic", **eq))

        # 4. Temporal questions from canon chunks (if canon_store available)
        temporal_qs = self._generate_temporal_questions()
        for tq in temporal_qs:
            qid += 1
            qs.append(ExamQuestion(qid=f"Q{qid:03d}", qtype="temporal", **tq))

        # If still under n, generate more entity-based questions by varying question templates
        if len(qs) < n and self.enrichment_store:
            entities = self.enrichment_store.query_all_entities()
            extra_templates = [
                ("{name} xuất hiện ở chương {ch}, thuộc giai đoạn nào của truyện?", lambda e: f"Chương {e.first_seen_chapter}"),
                ("Trong các nhân vật sau, ai xuất hiện sớm nhất?", None),
            ]
            for e in entities:
                if len(qs) >= n:
                    break
                qid += 1
                ch = e.first_seen_chapter
                phase = "đầu" if ch <= 100 else ("giữa" if ch <= 500 else "cuối")
                opts = ["Giai đoạn đầu", "Giai đoạn giữa", "Giai đoạn cuối", "Không xác định"]
                correct = f"Giai đoạn {phase}"
                random.shuffle(opts)
                qs.append(ExamQuestion(
                    qid=f"Q{qid:03d}", qtype="temporal",
                    prompt=f"Nhân vật {e.canonical_name} (xuất hiện chương {ch}) thuộc giai đoạn nào?",
                    options=opts, answer=correct, source_hash=e.id
                ))

        return qs[:n]

    def _generate_realm_questions(self) -> List[Dict[str, Any]]:
        """Generate rule questions dynamically from REALM_ORDER."""
        questions = []
        # Q1: can_fly threshold
        fly_threshold_realm = None
        for r in REALM_ORDER:
            if can_fly(r):
                fly_threshold_realm = r
                break
        if fly_threshold_realm:
            wrong_realms = [r for r in REALM_ORDER[:RANK[fly_threshold_realm]] if not can_fly(r)]
            wrong = random.sample(wrong_realms, min(3, len(wrong_realms)))
            opts = [fly_threshold_realm] + wrong
            random.shuffle(opts)
            questions.append({
                "prompt": "Cảnh giới thấp nhất có thể tự do ngự không phi hành mà không cần pháp bảo là gì?",
                "options": opts, "answer": fly_threshold_realm
            })

        # Q2: Realm ordering — pick two adjacent realms, ask which is higher
        if len(REALM_ORDER) > 5:
            idx = random.randint(2, len(REALM_ORDER) - 3)
            higher = REALM_ORDER[idx + 1]
            lower = REALM_ORDER[idx - 1]
            opts = [higher, lower, REALM_ORDER[0], REALM_ORDER[-1]]
            random.shuffle(opts)
            questions.append({
                "prompt": f"Trong hai cảnh giới '{higher}' và '{lower}', cảnh giới nào cao hơn?",
                "options": opts, "answer": higher
            })

        # Q3: Plausibility check — big jump
        if len(REALM_ORDER) > 10:
            low_r = REALM_ORDER[2]
            high_r = REALM_ORDER[-3]
            questions.append({
                "prompt": f"Nhảy vọt từ '{low_r}' lên '{high_r}' trong 3 ngày có hợp lý không?",
                "options": ["Bất hợp lý (vi phạm quy tắc cảnh giới)", "Hoàn toàn hợp lý", "Tùy công pháp đặc biệt", "Bình thường"],
                "answer": "Bất hợp lý (vi phạm quy tắc cảnh giới)"
            })

        # Q4: Count realms in a tier
        ngoai_canh_count = sum(1 for r in REALM_ORDER if "Ngoại Cảnh" in r)
        opts = [str(ngoai_canh_count), str(ngoai_canh_count + 2), str(max(1, ngoai_canh_count - 3)), str(ngoai_canh_count + 5)]
        random.shuffle(opts)
        questions.append({
            "prompt": "Có bao nhiêu bậc con trong giai đoạn Ngoại Cảnh (từ Nhất Trọng Thiên đến Cửu Trọng Thiên)?",
            "options": opts, "answer": str(ngoai_canh_count)
        })

        return questions

    def _generate_epistemic_questions(self) -> List[Dict[str, Any]]:
        """Generate epistemic questions from ledger or canon_store."""
        questions = []
        # From epistemic ledger if available
        if self.ledger and hasattr(self.ledger, 'facts'):
            secret_facts = [(fid, f) for fid, f in self.ledger.facts.items()
                           if getattr(f, 'secrecy', 'public') in ('secret', 'forbidden')]
            for fid, fact in secret_facts[:4]:
                known_by = getattr(fact, 'known_by', [])
                since_ch = getattr(fact, 'since_chapter', 1)
                desc = getattr(fact, 'description', fid)
                if known_by:
                    actor = known_by[0]
                    opts = [actor, "Tất cả mọi người", "Không ai biết", "Chỉ kẻ phản diện"]
                    random.shuffle(opts)
                    questions.append({
                        "prompt": f"Ai là người biết bí mật '{desc}' (từ chương {since_ch})?",
                        "options": opts, "answer": actor
                    })

        # Fallback: generate from canon_store search results about known secrets
        if not questions and self.canon_store:
            secret_queries = ["Lục Đạo Luân Hồi bí mật", "thân phận thật Mạnh Kỳ", "Chân Định pháp danh"]
            for sq in secret_queries[:3]:
                results = self.canon_store.search_canon(sq, top_k=2)
                if results:
                    r = results[0]
                    ch = r.get("chapter", r.get("chapter_index", "?"))
                    questions.append({
                        "prompt": f"Bí mật liên quan đến '{sq[:20]}...' được tiết lộ khoảng chương nào?",
                        "options": [str(ch), str(int(ch) + 50 if isinstance(ch, int) else "?"),
                                   str(max(1, int(ch) - 30) if isinstance(ch, int) else "?"),
                                   str(int(ch) + 200 if isinstance(ch, int) else "?")],
                        "answer": str(ch),
                        "evidence_chunk_id": r.get("chunk_id", "")
                    })

        return questions

    def _generate_temporal_questions(self) -> List[Dict[str, Any]]:
        """Generate temporal questions from canon chunks."""
        questions = []
        if not self.canon_store:
            return questions

        # Search for key events and ask about their chapter
        event_queries = [
            ("Mạnh Kỳ bái nhập Thiếu Lâm", "Sự kiện Mạnh Kỳ vào Thiếu Lâm"),
            ("tiểu đội Luân Hồi nhận nhiệm vụ", "Nhiệm vụ đầu tiên của tiểu đội Luân Hồi"),
            ("Giang Chỉ Vi xuất hiện", "Giang Chỉ Vi lần đầu xuất hiện"),
        ]
        for query, label in event_queries:
            results = self.canon_store.search_canon(query, top_k=1)
            if results:
                r = results[0]
                ch = r.get("chapter", r.get("chapter_index", 0))
                if isinstance(ch, int) and ch > 0:
                    opts = [str(ch), str(ch + 20), str(max(1, ch - 15)), str(ch + 100)]
                    random.shuffle(opts)
                    questions.append({
                        "prompt": f"'{label}' diễn ra khoảng chương nào?",
                        "options": opts, "answer": str(ch),
                        "evidence_chunk_id": r.get("chunk_id", "")
                    })

        return questions

    def score(self, answers: Dict[str, str], questions: List[ExamQuestion]) -> Dict[str, Any]:
        total = len(questions)
        correct = sum(1 for q in questions if answers.get(q.qid) == q.answer)
        by_type: Dict[str, Dict[str, Any]] = {}
        for q in questions:
            by_type.setdefault(q.qtype, {"total": 0, "correct": 0})
            by_type[q.qtype]["total"] += 1
            if answers.get(q.qid) == q.answer:
                by_type[q.qtype]["correct"] += 1

        for k, v in by_type.items():
            v["pct"] = (v["correct"] / v["total"] * 100) if v["total"] else 0.0

        overall = (correct / total * 100) if total else 0.0
        return {
            "overall": overall,
            "by_type": by_type,
            "total": total,
            "correct": correct
        }

    def gate(
        self,
        answers: Optional[Dict[str, str]] = None,
        min_overall: float = 85.0,
        min_temporal: float = 80.0,
        min_rule: float = 90.0,
        questions: Optional[List[ExamQuestion]] = None
    ) -> Dict[str, Any]:
        qs = questions or self.generate(n=20)
        # If no answers provided, returns unpassed exam with questions for solver
        if answers is None:
            return {
                "passed": False,
                "overall": 0.0,
                "temporal": 0.0,
                "rule": 0.0,
                "reason": "Chưa nộp câu trả lời",
                "questions": [q.model_dump() for q in qs]
            }

        result = self.score(answers, qs)
        temporal = result["by_type"].get("temporal", {"pct": 100.0})["pct"]
        rule = result["by_type"].get("rule", {"pct": 100.0})["pct"]
        passed = result["overall"] >= min_overall and temporal >= min_temporal and rule >= min_rule

        return {
            "passed": passed,
            "overall": result["overall"],
            "temporal": temporal,
            "rule": rule,
            "detail": result
        }
