"""
Seed script for PALP pilot data — DEVELOPMENT ONLY.

WARNING: This script creates test users with predictable passwords.
         NEVER run this in production.

Run: python manage.py shell < ../scripts/seed_data.py
"""
import os
import secrets
import sys
import django

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "palp.settings.development")
django.setup()

from django.conf import settings

if not settings.DEBUG:
    print("ERROR: seed_data.py must only run with DEBUG=True. Aborting.")
    sys.exit(1)

from accounts.models import User, StudentClass, ClassMembership, LecturerClassAssignment
from curriculum.models import Course, Concept, ConceptPrerequisite, Milestone, MicroTask, SupplementaryContent
from assessment.models import Assessment, AssessmentQuestion

SEED_PASSWORD = os.environ.get("SEED_PASSWORD", secrets.token_urlsafe(12))

print("Seeding PALP data...")
print(f"  Seed password: {SEED_PASSWORD}")

# Course
course, _ = Course.objects.get_or_create(
    code="SBVL",
    defaults={"name": "Sức Bền Vật Liệu", "description": "Học phần nền tảng về cơ học vật rắn biến dạng", "credits": 3},
)
print(f"  Course: {course}")

# Concepts (Knowledge Graph)
concepts_data = [
    ("C01", "Nội lực và biểu đồ nội lực", 1),
    ("C02", "Ứng suất và biến dạng", 2),
    ("C03", "Kéo - Nén đúng tâm", 3),
    ("C04", "Trạng thái ứng suất", 4),
    ("C05", "Đặc trưng hình học của mặt cắt ngang", 5),
    ("C06", "Uốn phẳng", 6),
    ("C07", "Uốn xiên", 7),
    ("C08", "Xoắn thuần túy", 8),
    ("C09", "Uốn và xoắn đồng thời", 9),
    ("C10", "Ổn định của thanh chịu nén", 10),
]

concepts = {}
for code, name, order in concepts_data:
    c, _ = Concept.objects.get_or_create(
        course=course, code=code, defaults={"name": name, "order": order}
    )
    concepts[code] = c

# Prerequisites
prereqs = [
    ("C02", "C01"), ("C03", "C02"), ("C04", "C02"),
    ("C05", "C01"), ("C06", "C05"), ("C06", "C03"),
    ("C07", "C06"), ("C08", "C04"), ("C09", "C06"),
    ("C09", "C08"), ("C10", "C03"),
]
for concept_code, prereq_code in prereqs:
    ConceptPrerequisite.objects.get_or_create(
        concept=concepts[concept_code], prerequisite=concepts[prereq_code]
    )

print(f"  Concepts: {len(concepts)}")

# Milestones
milestones_data = [
    ("M1: Nền tảng lực học", "Hiểu nội lực, ứng suất, biến dạng cơ bản", 1, 2, ["C01", "C02"]),
    ("M2: Thanh chịu lực đơn giản", "Phân tích kéo-nén và trạng thái ứng suất", 2, 3, ["C03", "C04"]),
    ("M3: Hình học mặt cắt", "Tính đặc trưng hình học MCN", 3, 4, ["C05"]),
    ("M4: Uốn cơ bản", "Phân tích uốn phẳng và uốn xiên", 4, 6, ["C06", "C07"]),
    ("M5: Xoắn và tổ hợp", "Xoắn thuần túy, uốn-xoắn đồng thời", 5, 8, ["C08", "C09"]),
    ("M6: Ổn định", "Ổn định thanh chịu nén", 6, 9, ["C10"]),
]

milestones = {}
for title, desc, order, week, concept_codes in milestones_data:
    m, _ = Milestone.objects.get_or_create(
        course=course, order=order,
        defaults={"title": title, "description": desc, "target_week": week},
    )
    m.concepts.set([concepts[c] for c in concept_codes])
    milestones[order] = m

print(f"  Milestones: {len(milestones)}")

# Micro-tasks (sample for M1)
tasks_m1 = [
    {
        "title": "Xác định phản lực liên kết",
        "concept": "C01", "difficulty": 1, "task_type": "quiz", "est": 5,
        "content": {
            "question": "Một dầm đơn giản chịu tải phân bố đều q. Phản lực tại gối A bằng?",
            "options": ["qL/2", "qL", "qL/4", "2qL"],
            "correct_answer": "qL/2",
        },
    },
    {
        "title": "Vẽ biểu đồ lực cắt Q",
        "concept": "C01", "difficulty": 2, "task_type": "calculation", "est": 10,
        "content": {
            "question": "Cho dầm console chịu lực tập trung P tại đầu tự do. Giá trị lực cắt Q tại ngàm?",
            "options": ["P", "-P", "0", "2P"],
            "correct_answer": "-P",
        },
    },
    {
        "title": "Phân biệt ứng suất pháp và tiếp",
        "concept": "C02", "difficulty": 1, "task_type": "quiz", "est": 5,
        "content": {
            "question": "Ứng suất pháp σ tác dụng theo phương nào so với mặt cắt?",
            "options": ["Vuông góc", "Song song", "Nghiêng 45°", "Tùy trường hợp"],
            "correct_answer": "Vuông góc",
        },
    },
    {
        "title": "Tính biến dạng dài tương đối",
        "concept": "C02", "difficulty": 2, "task_type": "calculation", "est": 8,
        "content": {
            "question": "Thanh thép dài L=2m, bị kéo dãn thêm ΔL=2mm. Biến dạng dài tương đối ε = ?",
            "options": ["0.001", "0.01", "0.1", "0.002"],
            "correct_answer": "0.001",
        },
    },
    {
        "title": "Tình huống: Kiểm tra cột chịu nén",
        "concept": "C03", "difficulty": 2, "task_type": "scenario", "est": 10,
        "content": {
            "question": "Cột bê tông MCN 300x300mm chịu lực nén N=450kN. Ứng suất pháp σ (MPa)?",
            "options": ["5.0", "15.0", "4.5", "1.5"],
            "correct_answer": "5.0",
        },
    },
]

for i, td in enumerate(tasks_m1):
    MicroTask.objects.get_or_create(
        milestone=milestones[1] if td["concept"] in ["C01", "C02"] else milestones[2],
        concept=concepts[td["concept"]],
        title=td["title"],
        defaults={
            "task_type": td["task_type"],
            "difficulty": td["difficulty"],
            "estimated_minutes": td["est"],
            "content": td["content"],
            "order": i + 1,
        },
    )

print(f"  Micro-tasks seeded")

# Supplementary content
supp_data = [
    ("C01", "Ôn lại: Cân bằng lực cơ bản", "text",
     "Nguyên lý cân bằng: Tổng các lực và tổng momen tác dụng lên vật rắn ở trạng thái cân bằng đều bằng 0. ΣF=0, ΣM=0."),
    ("C02", "Ví dụ minh họa: Ứng suất trong dây cáp cầu treo", "example",
     "Dây cáp cầu treo Thuận Phước (Đà Nẵng) chịu lực kéo lớn. Ứng suất σ = N/A, với N là lực kéo trong dây và A là diện tích mặt cắt ngang dây cáp."),
    ("C03", "Công thức: Điều kiện bền kéo-nén", "formula",
     "σ = N/A ≤ [σ], trong đó [σ] là ứng suất cho phép của vật liệu. Với thép CT3: [σ] = 160 MPa."),
]

for concept_code, title, ctype, body in supp_data:
    SupplementaryContent.objects.get_or_create(
        concept=concepts[concept_code], title=title,
        defaults={"content_type": ctype, "body": body, "difficulty_target": 1},
    )

print(f"  Supplementary content seeded")

# Assessment
assessment, _ = Assessment.objects.get_or_create(
    course=course, title="Đánh giá đầu vào SBVL",
    defaults={"description": "Assessment 15 phút để xác định năng lực nền", "time_limit_minutes": 15},
)

questions_data = [
    ("C01", "multiple_choice", "Đơn vị đo lực trong hệ SI là gì?",
     ["Newton (N)", "Pascal (Pa)", "Joule (J)", "Watt (W)"], "Newton (N)"),
    ("C01", "true_false", "Phản lực liên kết luôn vuông góc với bề mặt tiếp xúc.",
     ["Đúng", "Sai"], "Sai"),
    ("C02", "multiple_choice", "Công thức tính ứng suất pháp trên mặt cắt ngang?",
     ["σ = N/A", "σ = M/W", "σ = Q/A", "σ = E·ε"], "σ = N/A"),
    ("C02", "multiple_choice", "Mô đun đàn hồi E của thép khoảng bao nhiêu?",
     ["2.1 × 10⁵ MPa", "2.1 × 10³ MPa", "2.1 × 10⁷ MPa", "21 MPa"], "2.1 × 10⁵ MPa"),
    ("C03", "multiple_choice", "Điều kiện bền khi kéo-nén đúng tâm?",
     ["σ = N/A ≤ [σ]", "τ = Q/A ≤ [τ]", "σ = M/W ≤ [σ]", "Δl = NL/EA ≤ [Δl]"], "σ = N/A ≤ [σ]"),
    ("C05", "multiple_choice", "Momen quán tính của hình chữ nhật b×h đối với trục qua trọng tâm?",
     ["bh³/12", "bh²/6", "bh/2", "b²h/12"], "bh³/12"),
    ("C06", "multiple_choice", "Trong uốn phẳng, ứng suất pháp lớn nhất xuất hiện ở đâu?",
     ["Thớ ngoài cùng", "Trục trung hòa", "1/4 chiều cao", "Tùy tiết diện"], "Thớ ngoài cùng"),
    ("C08", "multiple_choice", "Công thức ứng suất tiếp khi xoắn thuần túy tiết diện tròn?",
     ["τ = Mz·ρ/Jp", "τ = Q·Sz/(Iz·b)", "τ = N/A", "τ = T/2At"], "τ = Mz·ρ/Jp"),
    ("C01", "multiple_choice", "Momen uốn tại tiết diện giữa dầm đơn giản chịu lực tập trung P ở giữa nhịp?",
     ["PL/4", "PL/2", "PL/8", "PL"], "PL/4"),
    ("C04", "multiple_choice", "Trong trạng thái ứng suất phẳng, số thành phần ứng suất độc lập là?",
     ["3", "4", "6", "2"], "3"),
]

for i, (cc, qt, text, options, correct) in enumerate(questions_data):
    AssessmentQuestion.objects.get_or_create(
        assessment=assessment, order=i + 1,
        defaults={
            "concept": concepts[cc],
            "question_type": qt,
            "text": text,
            "options": options,
            "correct_answer": correct,
        },
    )

print(f"  Assessment: {assessment.questions.count()} questions")

# Classes and users
cls1, _ = StudentClass.objects.get_or_create(name="22KT1", defaults={"academic_year": "2025-2026"})
cls2, _ = StudentClass.objects.get_or_create(name="22KT2", defaults={"academic_year": "2025-2026"})

admin_user = User.objects.filter(is_superuser=True).first()
if not admin_user:
    admin_user = User.objects.create_superuser(
        username="admin", email="admin@dau.edu.vn", password=SEED_PASSWORD,
        first_name="Admin", last_name="PALP", role="admin",
    )
    print(f"  Admin user created: admin / {SEED_PASSWORD}")

lecturer1, created = User.objects.get_or_create(
    username="gv.nguyen", defaults={
        "email": "nguyen@dau.edu.vn", "first_name": "Nguyễn", "last_name": "Văn A",
        "role": "lecturer",
    },
)
if created:
    lecturer1.set_password(SEED_PASSWORD)
    lecturer1.save()
    print(f"  Lecturer created: gv.nguyen / {SEED_PASSWORD}")

LecturerClassAssignment.objects.get_or_create(lecturer=lecturer1, student_class=cls1)
LecturerClassAssignment.objects.get_or_create(lecturer=lecturer1, student_class=cls2)

E2E_PASSWORD = "testpass123"

e2e_student, created = User.objects.get_or_create(
    username="sv_test", defaults={
        "email": "sv_test@sv.dau.edu.vn",
        "first_name": "Test",
        "last_name": "Student",
        "role": "student",
        "student_id": "22KTE2E",
    },
)
if created:
    e2e_student.set_password(E2E_PASSWORD)
    e2e_student.save()
    print(f"  E2E student created: sv_test / {E2E_PASSWORD}")
ClassMembership.objects.get_or_create(student=e2e_student, student_class=cls1)

e2e_lecturer, created = User.objects.get_or_create(
    username="gv_test", defaults={
        "email": "gv_test@dau.edu.vn",
        "first_name": "Test",
        "last_name": "Lecturer",
        "role": "lecturer",
    },
)
if created:
    e2e_lecturer.set_password(E2E_PASSWORD)
    e2e_lecturer.save()
    print(f"  E2E lecturer created: gv_test / {E2E_PASSWORD}")
LecturerClassAssignment.objects.get_or_create(lecturer=e2e_lecturer, student_class=cls1)
LecturerClassAssignment.objects.get_or_create(lecturer=e2e_lecturer, student_class=cls2)

for i in range(1, 31):
    username = f"sv{i:03d}"
    student, created = User.objects.get_or_create(
        username=username, defaults={
            "email": f"{username}@sv.dau.edu.vn",
            "first_name": f"SV{i:03d}",
            "last_name": "Pilot",
            "role": "student",
            "student_id": f"22KT{i:04d}",
        },
    )
    if created:
        student.set_password(SEED_PASSWORD)
        student.save()
    target_class = cls1 if i <= 15 else cls2
    ClassMembership.objects.get_or_create(student=student, student_class=target_class)

print(f"  30 students seeded across 2 classes")
print("Seed complete!")
