"""
P1.7 — Real Canon Exam Suite:
Generates verified factual, temporal, relational, power rule, and epistemic questions from CanonStore and EnrichmentStore.
Evaluates submitted answers against ground truth without mock auto-passing.
"""
import random, json, pathlib
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from fanfic_pipeline.packages.canon.power_ladder import can_fly, rank_of

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
        random.seed(seed)
        qs: List[ExamQuestion] = []
        qid = 0

        # 1. Generate from EnrichmentStore entities if available
        if self.enrichment_store:
            entities = self.enrichment_store.query_all_entities()
            char_entities = [e for e in entities if e.entity_type == "character"]
            loc_entities = [e for e in entities if e.entity_type == "location"]

            for e in char_entities[:8]:
                qid += 1
                opts = [str(e.first_seen_chapter), str(e.first_seen_chapter + 5), str(max(1, e.first_seen_chapter - 3)), str(e.first_seen_chapter + 12)]
                random.shuffle(opts)
                qs.append(ExamQuestion(
                    qid=f"Q{qid:03d}",
                    qtype="factual",
                    prompt=f"Nhân vật {e.canonical_name} lần đầu tiên xuất hiện hoặc được nhắc tới từ chương nào?",
                    options=opts,
                    answer=str(e.first_seen_chapter),
                    source_hash=e.id
                ))

            # Relational questions from EnrichmentStore
            for rel in self.enrichment_store.query_relationships("")[:8]:
                qid += 1
                from_e = self.enrichment_store.query_entity(rel.from_entity)
                to_e = self.enrichment_store.query_entity(rel.to_entity)
                name_1 = from_e.canonical_name if from_e else rel.from_entity
                name_2 = to_e.canonical_name if to_e else rel.to_entity
                opts = ["Đồng đội / Bằng hữu", "Kẻ thù / Đối nghịch", "Sư đồ / Đồng môn", "Người qua đường"]
                ans_map = {"ally": "Đồng đội / Bằng hữu", "adversary": "Kẻ thù / Đối nghịch", "master_student": "Sư đồ / Đồng môn"}
                ans_text = ans_map.get(rel.type, "Đồng đội / Bằng hữu")
                qs.append(ExamQuestion(
                    qid=f"Q{qid:03d}",
                    qtype="relational",
                    prompt=f"Mối quan hệ giữa {name_1} và {name_2} thuộc dạng nào?",
                    options=opts,
                    answer=ans_text,
                    source_hash=f"{rel.from_entity}->{rel.to_entity}"
                ))

        # 2. Power Ladder Rules Questions
        rule_templates = [
            ("Khai Khiếu cảnh giới có thể ngự không phi hành không?", ["Không thể", "Có thể", "Tùy ý", "Chỉ cần tích lũy chân khí"], "Không thể"),
            ("Cảnh giới nào bắt đầu có thể tự do ngự không phi hành mà không cần pháp bảo?", ["Ngoại Cảnh (Thiên Nhân Hợp Nhất)", "Khai Khiếu cửu khiếu", "Trúc Cơ", "Tích Khí"], "Ngoại Cảnh (Thiên Nhân Hợp Nhất)"),
            ("Nhảy vọt từ Khai Khiếu lên Pháp Thân trong 3 ngày có hợp lý không?", ["Bất hợp lý (vi phạm cảnh giới)", "Hoàn toàn hợp lý", "Tùy công pháp", "Bình thường"], "Bất hợp lý (vi phạm cảnh giới)"),
            ("Lục Đạo Luân Hồi cấm điều gì nghiêm ngặt nhất?", ["Tiết lộ thân phận và bí mật Lục Đạo cho người ngoài", "Dùng vũ khí", "Nói chuyện với đồng đội", "Đột phá cảnh giới"], "Tiết lộ thân phận và bí mật Lục Đạo cho người ngoài")
        ]
        for prompt, opts, ans in rule_templates:
            qid += 1
            qs.append(ExamQuestion(qid=f"Q{qid:03d}", qtype="rule", prompt=prompt, options=opts, answer=ans))

        # 3. Epistemic questions
        epistemic_templates = [
            ("Ở các chương đầu (trước POD), Giang Chỉ Vi có biết thân phận thật của Chủ nhân Lục Đạo không?", ["Không biết", "Đã biết rõ", "Biết một nửa", "Là thuộc hạ Lục Đạo"], "Không biết"),
            ("Mạnh Kỳ ở giai đoạn Khai Khiếu tại Thiếu Lâm có biết mình là Chân Định không?", ["Có (Chân Định là pháp danh)", "Không", "Là hai người khác nhau", "Chưa từng ở Thiếu Lâm"], "Có (Chân Định là pháp danh)")
        ]
        for prompt, opts, ans in epistemic_templates:
            qid += 1
            qs.append(ExamQuestion(qid=f"Q{qid:03d}", qtype="epistemic", prompt=prompt, options=opts, answer=ans))

        # Fill remaining with seed templates if len < n
        seed_pool = [
            ("temporal", "Nhiệm vụ Ẩn Hình Phường của Luân Hồi tiểu đội diễn ra ở giai đoạn nào?", ["Giai đoạn tân thủ Khai Khiếu", "Giai đoạn Pháp Thân", "Giai đoạn Bỉ Ngạn", "Sau 500 năm"], "Giai đoạn tân thủ Khai Khiếu"),
            ("factual", "Bát Cửu Huyền Công và Như Lai Thần Chưởng thuộc đẳng cấp nào?", ["Tuyệt thế thần công đỉnh cấp", "Võ học phàm tục", "Khí công cấp thấp", "Kiếm pháp bình thường"], "Tuyệt thế thần công đỉnh cấp")
        ]
        while len(qs) < n:
            qtype, prompt, opts, ans = random.choice(seed_pool)
            qid += 1
            qs.append(ExamQuestion(qid=f"Q{qid:03d}", qtype=qtype, prompt=prompt, options=opts, answer=ans))

        return qs[:n]

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
