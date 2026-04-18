# PALP — Personalized Adaptive Learning Platform
## Tổng quan hệ thống chi tiết

---

## 1. Giới thiệu dự án

PALP (Personalized Adaptive Learning Platform) là một nền tảng EdTech được thiết kế và phát triển dành riêng cho chương trình pilot tại Đại học Kiến trúc Đà Nẵng. Hệ thống tập trung vào môn học Sức Bền Vật Liệu, phục vụ khoảng 60 đến 90 sinh viên và 2 đến 3 giảng viên trong vòng 10 tuần thử nghiệm.

### 1.1 Vấn đề cần giải quyết

Trong giáo dục truyền thống, tất cả sinh viên đều học cùng một lộ trình, cùng tốc độ, bất kể trình độ đầu vào khác nhau. Điều này dẫn đến việc sinh viên giỏi cảm thấy nhàm chán, sinh viên yếu bị bỏ lại phía sau, và giảng viên không có công cụ để phát hiện sớm sinh viên gặp khó khăn.

PALP giải quyết vấn đề này bằng cách cá nhân hóa trải nghiệm học tập cho từng sinh viên thông qua đánh giá đầu vào, lộ trình thích ứng dựa trên thuật toán Bayesian Knowledge Tracing (BKT), hệ thống micro-task và milestone, dashboard cảnh báo sớm cho giảng viên, theo dõi sự kiện và phân tích KPI, cùng với tính năng chăm sóc sức khỏe tinh thần cho sinh viên.

### 1.2 Triết lý thiết kế

PALP được xây dựng trên năm nguyên tắc cốt lõi. Thứ nhất, đặt việc học lên trước gamification, nghĩa là hệ thống ưu tiên hiệu quả học tập thực sự thay vì các yếu tố game hóa bề mặt. Thứ hai, con người luôn nằm trong vòng lặp, giảng viên luôn có quyền can thiệp và điều chỉnh lộ trình của sinh viên. Thứ ba, các can thiệp phải giải thích được, mọi quyết định của hệ thống đều có lý do rõ ràng mà giảng viên và sinh viên có thể hiểu. Thứ tư, quyền riêng tư theo thiết kế, bảo vệ dữ liệu cá nhân được tích hợp từ đầu chứ không phải bổ sung sau. Thứ năm, MVP trước, bắt đầu với luật và BKT đơn giản trước khi mở rộng sang machine learning phức tạp hơn.

### 1.3 Mục tiêu KPI pilot

Hệ thống đặt ra các mục tiêu đo lường cụ thể cho giai đoạn pilot. Tăng ít nhất 20% thời gian học tập chủ động mỗi tuần so với baseline. Đạt tỷ lệ hoàn thành micro-task từ 70% trở lên. Chỉ số hài lòng CSAT đạt tối thiểu 4.0 trên 5.0. Giảng viên sử dụng dashboard ít nhất 2 lần mỗi tuần. Phát hiện sinh viên gặp khó khăn nhanh hơn so với phương pháp truyền thống.

---

## 2. Kiến trúc công nghệ

### 2.1 Stack công nghệ tổng quan

PALP sử dụng kiến trúc client-server hiện đại với các công nghệ sau.

Về frontend, hệ thống sử dụng Next.js 14 với App Router, React 18, TypeScript để đảm bảo type safety, Tailwind CSS cho styling, Radix UI làm thư viện component headless, Recharts cho biểu đồ trực quan hóa dữ liệu, và Zustand cho quản lý state.

Về backend, hệ thống dùng Python 3.12, Django 5.1 với Django REST Framework để xây dựng REST API, djangorestframework-simplejwt cho xác thực JWT, Celery kết hợp django-celery-beat cho xử lý tác vụ nền và lập lịch, drf-spectacular cho tài liệu OpenAPI tự động, và django-prometheus cho metrics.

Về cơ sở dữ liệu, PostgreSQL 16 được chọn làm database chính nhờ tính ACID, hỗ trợ JSON field tốt, và khả năng mở rộng. Redis 7 đóng vai trò vừa là cache layer vừa là message broker cho Celery.

Về data và ML, hệ thống sử dụng NumPy và Pandas cho xử lý dữ liệu, scikit-learn cho một số bước ETL như KNNImputer xử lý dữ liệu thiếu.

Về observability, Sentry được dùng cho error tracking trong production, Prometheus middleware cho metrics, và hệ thống custom metrics riêng.

Về DevOps, hệ thống sử dụng Docker và docker-compose cho cả môi trường development và production, Nginx làm reverse proxy cho production, và GitHub Actions cho CI/CD pipeline.

### 2.2 Tại sao chọn stack này

Django được chọn vì ORM mạnh mẽ, admin panel sẵn có cho quản lý dữ liệu, hệ sinh thái package phong phú, và phù hợp với quy mô pilot. Next.js được chọn vì hỗ trợ server-side rendering tốt, routing hiện đại với App Router, và developer experience tuyệt vời. PostgreSQL cộng Redis là sự kết hợp giữa database ACID đáng tin cậy và cache tốc độ cao. Celery được chọn thay vì Kafka vì phù hợp hơn với quy mô pilot, đơn giản hơn trong vận hành mà vẫn đáp ứng được nhu cầu xử lý batch.

### 2.3 Kiến trúc triển khai

Hệ thống có ba cấp triển khai. Môi trường development sử dụng docker-compose với các service bao gồm PostgreSQL, Redis, Django development server, Celery worker, Celery Beat scheduler, Next.js dev server, và service backup database tự động.

Môi trường production bổ sung thêm Nginx reverse proxy xử lý SSL/TLS, Gunicorn thay cho Django dev server, healthcheck cho mỗi service, giới hạn tài nguyên cho container, và backup database hằng ngày theo lịch.

Hệ thống cung cấp ba endpoint health check. Endpoint liveness tại /api/health/ kiểm tra service có đang chạy không. Endpoint readiness tại /api/health/ready/ kiểm tra database và Redis đã sẵn sàng chưa. Endpoint deep tại /api/health/deep/ kiểm tra toàn bộ hệ thống bao gồm cả Celery queue.

---

## 3. Cấu trúc dự án

Dự án được tổ chức thành các thư mục chính như sau.

Thư mục backend chứa toàn bộ Django project với tên palp. Bên trong có 9 Django app chính bao gồm accounts, assessment, adaptive, curriculum, dashboard, analytics, events, wellbeing, và privacy. Ngoài ra có thư mục core chứa model trừu tượng dùng chung, thư mục palp chứa settings, URLs, middleware, Celery config, thư mục openapi chứa schema baseline cho contract CI, và thư mục tests chứa integration, contract, security, load, data QA, và recovery tests.

Thư mục frontend chứa Next.js app với cấu trúc src/app cho pages, components cho UI reusable, hooks cho state management, và lib cho utilities và API client.

Thư mục nginx chứa cấu hình reverse proxy cho production. Thư mục scripts chứa các script tiện ích như seed data, backup, release gate. Thư mục docs chứa tất cả tài liệu dự án. Và thư mục .github chứa CI/CD workflows và PR template.

---

## 4. Backend — Chi tiết từng module

### 4.1 Accounts (Quản lý người dùng)

Module accounts quản lý toàn bộ vòng đời người dùng trong hệ thống. Model User mở rộng từ Django AbstractUser với các trường bổ sung quan trọng. Trường role phân biệt ba vai trò chính là student, lecturer, và admin. Trường student_id được mã hóa bằng EncryptedCharField để bảo vệ thông tin cá nhân. Trường student_id_hash lưu hash của mã sinh viên để tìm kiếm nhanh mà không cần giải mã. Trường phone cũng được mã hóa. Trường consent_given và consent_given_at theo dõi việc người dùng đã đồng ý điều khoản chưa. Trường is_deleted và deleted_at hỗ trợ soft delete.

Ngoài User, module còn có model StudentClass đại diện cho lớp học với tên và năm học. Model ClassMembership liên kết sinh viên với lớp. Model LecturerClassAssignment phân công giảng viên phụ trách lớp.

Về authentication, hệ thống sử dụng JWT thông qua httpOnly cookies. Khi đăng nhập, server trả về hai cookie là palp_access chứa access token và palp_refresh chứa refresh token. Cookie httpOnly đảm bảo JavaScript phía client không thể đọc token, chống XSS hiệu quả. Khi access token hết hạn, client tự động gọi endpoint refresh để lấy token mới. Đăng xuất sẽ blacklist refresh token.

Hệ thống phân quyền RBAC được triển khai qua các permission class tùy chỉnh. IsStudent chỉ cho phép sinh viên. IsLecturer chỉ cho phép giảng viên. IsAdminUser cho admin. IsLecturerOrAdmin cho giảng viên hoặc admin. IsClassMember kiểm tra người dùng có thuộc lớp hay không. IsStudentInLecturerClass đảm bảo giảng viên chỉ truy cập dữ liệu sinh viên trong lớp mình phụ trách. IsOwnAlertClass kiểm tra alert thuộc lớp của giảng viên.

API endpoints của accounts bao gồm đăng nhập tại POST /api/auth/login/, đăng xuất tại POST /api/auth/logout/, refresh token tại POST /api/auth/token/refresh/, đăng ký tại POST /api/auth/register/, xem và cập nhật hồ sơ tại GET/PUT/PATCH /api/auth/profile/, cấp consent tại POST /api/auth/consent/, xem danh sách lớp tại GET /api/auth/classes/, xem sinh viên trong lớp tại GET /api/auth/classes/{class_id}/students/, xuất dữ liệu cá nhân tại GET /api/auth/export/my-data/, xuất dữ liệu lớp tại GET /api/auth/export/class/{class_id}/, và xóa dữ liệu cá nhân tại POST /api/auth/delete-my-data/.

### 4.2 Assessment (Đánh giá đầu vào)

Module assessment phục vụ đánh giá trình độ ban đầu của sinh viên trước khi bắt đầu lộ trình học. Model Assessment đại diện cho một bài đánh giá, liên kết với khóa học, có tiêu đề, mô tả, giới hạn thời gian tính bằng phút, điểm đạt, và trạng thái hoạt động.

Model AssessmentQuestion chứa câu hỏi của bài đánh giá, liên kết với concept cụ thể trong chương trình. Mỗi câu hỏi có loại (trắc nghiệm, đúng sai, hoặc kéo thả), nội dung, các lựa chọn lưu dạng JSON, đáp án đúng, giải thích, thứ tự, và số điểm.

Model AssessmentSession theo dõi phiên làm bài của sinh viên. Mỗi phiên có trạng thái (đang làm, hoàn thành, v.v.), version, thời điểm bắt đầu, hoàn thành, nộp bài, tổng điểm, và tổng thời gian làm bài tính bằng giây.

Model AssessmentResponse ghi lại từng câu trả lời của sinh viên trong phiên làm bài, bao gồm câu hỏi nào, đáp án gì, đúng hay sai, và thời gian trả lời.

Model LearnerProfile được tạo ra sau khi hoàn thành đánh giá, chứa kết quả phân tích bao gồm điểm tổng thể, mastery ban đầu, điểm mạnh, điểm yếu, và concept khuyến nghị bắt đầu.

API endpoints bao gồm xem danh sách bài đánh giá tại GET /api/assessment/, xem câu hỏi tại GET /api/assessment/{pk}/questions/, bắt đầu làm bài tại POST /api/assessment/{pk}/start/, nộp từng câu trả lời tại POST /api/assessment/sessions/{session_id}/answer/, hoàn thành bài tại POST /api/assessment/sessions/{session_id}/complete/, xem lịch sử phiên làm bài tại GET /api/assessment/my-sessions/, và xem learner profile tại GET /api/assessment/profile/{course_id}/.

### 4.3 Adaptive (Học thích ứng — Trái tim của hệ thống)

Module adaptive là thành phần cốt lõi nhất của PALP, nơi thuật toán Bayesian Knowledge Tracing (BKT) được triển khai để cá nhân hóa lộ trình học tập.

Bayesian Knowledge Tracing là một mô hình xác suất theo dõi mức độ thành thạo (mastery) của sinh viên đối với từng concept. Mô hình sử dụng bốn tham số. Tham số p_mastery là xác suất sinh viên đã thành thạo concept, khởi tạo từ kết quả đánh giá đầu vào. Tham số p_guess là xác suất sinh viên đoán đúng dù chưa thành thạo. Tham số p_slip là xác suất sinh viên trả lời sai dù đã thành thạo. Tham số p_transit là xác suất chuyển từ chưa thành thạo sang thành thạo sau mỗi lần thực hành.

Sau mỗi lần sinh viên hoàn thành một task, BKT cập nhật p_mastery dựa trên kết quả đúng hay sai. Nếu đúng, p_mastery tăng lên. Nếu sai, p_mastery có thể giảm hoặc giữ nguyên tùy thuộc vào các tham số khác.

Model MasteryState lưu trạng thái mastery hiện tại của sinh viên cho từng concept, bao gồm tất cả bốn tham số BKT, số lần thử, số lần đúng, phiên bản, và thời điểm cập nhật cuối.

Logic pathway quyết định bước tiếp theo cho sinh viên dựa trên mastery. Khi p_mastery dưới 0.60, sinh viên được xem là chưa nắm vững, hệ thống cung cấp nội dung bổ sung (supplement) như tài liệu tham khảo, video giải thích, bài tập thêm. Khi p_mastery từ 0.60 đến 0.85, sinh viên tiếp tục lộ trình bình thường (continue) với các task ở độ khó phù hợp. Khi p_mastery trên 0.85, sinh viên đã thành thạo và được chuyển sang concept tiếp theo (advance).

Model TaskAttempt ghi lại mỗi lần sinh viên làm task, bao gồm điểm, điểm tối đa, thời gian làm, số gợi ý đã dùng, đúng hay sai, đáp án, và số lần thử.

Model ContentIntervention ghi lại các can thiệp nội dung mà hệ thống tự động đề xuất, bao gồm loại can thiệp, luật nguồn, phiên bản luật, nội dung, mastery tại thời điểm kích hoạt, mastery trước và sau can thiệp, giải thích, và phản hồi của sinh viên về tính hữu ích.

Model StudentPathway theo dõi lộ trình tổng thể của sinh viên trong khóa học, bao gồm concept hiện tại, milestone hiện tại, độ khó hiện tại, số concept đã hoàn thành, số milestone đã hoàn thành, số task đã hoàn thành, lịch sử độ khó, và trạng thái hoạt động.

Model PathwayOverride cho phép giảng viên can thiệp thủ công vào lộ trình của sinh viên, ghi đè quyết định của thuật toán với lý do cụ thể, các tham số điều chỉnh, thời hạn áp dụng.

Mastery state được cache trong Redis với TTL 5 phút để tối ưu hiệu năng truy vấn thường xuyên.

API endpoints bao gồm xem mastery tại GET /api/adaptive/mastery/, nộp bài tập tại POST /api/adaptive/submit/, xem lộ trình tại GET /api/adaptive/pathway/{course_id}/, lấy task tiếp theo tại GET /api/adaptive/next-task/{course_id}/, xem lịch sử thử tại GET /api/adaptive/attempts/, xem can thiệp tại GET /api/adaptive/interventions/, và giảng viên xem mastery sinh viên tại GET /api/adaptive/student/{student_id}/mastery/.

### 4.4 Curriculum (Chương trình học)

Module curriculum quản lý toàn bộ nội dung học tập được cấu trúc theo mô hình backward design.

Model Course đại diện cho khóa học, trong pilot này là Sức Bền Vật Liệu. Model Enrollment quản lý việc sinh viên đăng ký khóa học.

Model Concept đại diện cho một khái niệm kiến thức trong khóa học. Mỗi concept có tên, mô tả, thứ tự, và thuộc về một khóa học. Model ConceptPrerequisite định nghĩa quan hệ tiên quyết giữa các concept, tạo thành đồ thị kiến thức (knowledge graph) xác định thứ tự học logic.

Model Milestone là cột mốc lớn trong lộ trình học, nhóm nhiều concept liên quan lại với nhau. Mỗi milestone có tên, mô tả, thứ tự, và thuộc về một khóa học.

Model MicroTask là đơn vị học tập nhỏ nhất, mỗi task thuộc về một milestone và liên kết với một concept cụ thể. Task có các thuộc tính như tiêu đề, nội dung, loại (quiz, bài tập, v.v.), độ khó, điểm tối đa, và thời gian ước tính.

Model SupplementaryContent chứa tài liệu bổ sung cho mỗi concept, được sử dụng khi hệ thống adaptive quyết định sinh viên cần hỗ trợ thêm. Tài liệu có thể là video, bài đọc, bài tập thêm, hoặc liên kết ngoài.

API endpoints bao gồm danh sách khóa học tại GET /api/curriculum/courses/, chi tiết khóa tại GET /api/curriculum/courses/{pk}/, concepts theo khóa tại GET /api/curriculum/courses/{course_id}/concepts/, milestones theo khóa tại GET /api/curriculum/courses/{course_id}/milestones/, nội dung bổ sung theo concept tại GET /api/curriculum/concepts/{concept_id}/content/, enrollments của tôi tại GET /api/curriculum/my-enrollments/, và CRUD tasks tại /api/curriculum/tasks/ (giảng viên và admin có quyền tạo, sửa, xóa).

### 4.5 Dashboard (Bảng điều khiển giảng viên)

Module dashboard cung cấp công cụ cảnh báo sớm và can thiệp cho giảng viên.

Hệ thống early warning tự động phân tích dữ liệu sinh viên và tạo cảnh báo theo mức độ nghiêm trọng. Mức RED là cảnh báo nghiêm trọng nhất, ví dụ sinh viên không hoạt động quá lâu hoặc thử lại quá nhiều lần mà vẫn sai. Mức YELLOW là cảnh báo mức trung bình, ví dụ tiến độ milestone chậm hơn kỳ vọng. Các quy tắc cảnh báo dựa trên ngưỡng thời gian không hoạt động, số lần thử lại, và độ trễ milestone.

Model Alert lưu cảnh báo cho từng sinh viên với mức nghiêm trọng, lý do, và trạng thái (mới, đã xem, đã dismiss). Model InterventionAction ghi lại hành động can thiệp của giảng viên đối với từng cảnh báo.

Việc tính toán early warning được thực hiện qua Celery task chạy định kỳ hằng đêm, gọi hàm compute_early_warnings trong dashboard/services.py.

API endpoints bao gồm tổng quan lớp tại GET /api/dashboard/class/{class_id}/overview/, danh sách cảnh báo tại GET /api/dashboard/alerts/, dismiss cảnh báo tại POST /api/dashboard/alerts/{pk}/dismiss/, tạo can thiệp tại POST /api/dashboard/interventions/, lịch sử can thiệp tại GET /api/dashboard/interventions/history/, và cập nhật follow-up tại PATCH /api/dashboard/interventions/{pk}/follow-up/.

### 4.6 Analytics (Phân tích và báo cáo)

Module analytics quản lý KPI, báo cáo pilot, chất lượng dữ liệu, và quy trình ETL.

Model KPIDefinition định nghĩa từng KPI với mã code, tên, mô tả, công thức tính, và nguồn dữ liệu. Model KPIVersion theo dõi phiên bản KPI qua thời gian để đảm bảo tính nhất quán. Model KPILineageLog ghi lại lịch sử thay đổi và xuất xứ dữ liệu KPI.

Model PilotReport chứa báo cáo pilot định kỳ, tổng hợp dữ liệu từ nhiều nguồn. Model DataQualityLog ghi lại kết quả kiểm tra chất lượng dữ liệu. Model ETLRun theo dõi các lần chạy ETL pipeline.

Hệ thống có năm KPI pilot chính được theo dõi liên tục: thời gian học tập chủ động, tỷ lệ hoàn thành micro-task, độ chính xác của adaptive pathway, tần suất sử dụng dashboard của giảng viên, và mức độ hài lòng của sinh viên.

API endpoints bao gồm KPI theo lớp tại GET /api/analytics/kpi/{class_id}/, registry KPI tại GET /api/analytics/kpi-registry/, chi tiết KPI tại GET /api/analytics/kpi-registry/{code}/, lineage tại GET /api/analytics/kpi-lineage/, báo cáo tại GET /api/analytics/reports/, và chất lượng dữ liệu tại GET /api/analytics/data-quality/.

### 4.7 Events (Theo dõi sự kiện)

Module events là hệ thống event tracking thu thập mọi hành động quan trọng trong hệ thống phục vụ phân tích.

Model EventLog ghi lại từng sự kiện với nhiều trường chi tiết bao gồm tên sự kiện, phiên bản sự kiện, timestamp UTC, loại actor (student, lecturer, system), actor cụ thể, session ID, khóa học, lớp, concept, task, trạng thái mastery tại thời điểm sự kiện, các thuộc tính bổ sung dạng JSON, idempotency key để tránh trùng lặp, và thời điểm xác nhận.

Hệ thống hỗ trợ hai cách ghi sự kiện. API track tại POST /api/events/track/ ghi từng sự kiện đơn lẻ. API batch tại POST /api/events/batch/ ghi nhiều sự kiện cùng lúc, tối ưu cho frontend gửi hàng loạt. Cả hai đều hỗ trợ idempotency để tránh ghi trùng khi có retry.

Hệ thống emitter trong events/emitter.py xử lý emit events với idempotency check và custom metrics cho Prometheus.

API endpoints bao gồm ghi sự kiện tại POST /api/events/track/, ghi batch tại POST /api/events/batch/, sự kiện của tôi tại GET /api/events/my/, và giảng viên xem sự kiện sinh viên tại GET /api/events/student/{student_id}/.

### 4.8 Wellbeing (Chăm sóc sức khỏe)

Module wellbeing theo dõi thời gian học liên tục của sinh viên và gửi nhắc nhở nghỉ ngơi khi vượt ngưỡng 50 phút (cấu hình trong settings).

Model WellbeingNudge đại diện cho lời nhắc nghỉ được gửi đến sinh viên.

API endpoints bao gồm kiểm tra và tạo nudge tại POST /api/wellbeing/check/, phản hồi nudge tại POST /api/wellbeing/nudge/{pk}/respond/, và xem lịch sử nudge tại GET /api/wellbeing/my/.

### 4.9 Privacy (Quyền riêng tư)

Module privacy quản lý toàn bộ khía cạnh quyền riêng tư và tuân thủ bảo vệ dữ liệu.

Model ConsentRecord ghi lại từng lần sinh viên đồng ý hoặc rút đồng ý, bao gồm phiên bản consent, mục đích cụ thể, và thời điểm. Model AuditLog ghi lại mọi truy cập vào dữ liệu nhạy cảm. Model PrivacyIncident ghi lại sự cố bảo mật dữ liệu với SLA 48 giờ xử lý. Model DataDeletionRequest quản lý yêu cầu xóa dữ liệu cá nhân.

Middleware ConsentGateMiddleware chặn truy cập vào các endpoint xử lý PII nếu người dùng chưa cấp consent. Middleware AuditMiddleware tự động ghi log khi truy cập các đường dẫn nhạy cảm được cấu hình trong AUDIT_SENSITIVE_PREFIXES.

API endpoints bao gồm quản lý consent tại /api/privacy/consent/, lịch sử consent tại GET /api/privacy/consent/history/, xuất dữ liệu tại POST /api/privacy/export/, xóa dữ liệu tại POST /api/privacy/delete/, danh sách yêu cầu xóa tại GET /api/privacy/delete/requests/, audit log tại GET /api/privacy/audit-log/, và quản lý sự cố tại /api/privacy/incidents/.

### 4.10 Core và PALP Project

Module core cung cấp model trừu tượng TimeStampedModel với hai trường created_at và updated_at được kế thừa bởi tất cả model khác trong hệ thống.

Package palp chứa cấu hình dự án bao gồm settings cho các môi trường (base, development, test, production), URL routing chính, middleware tùy chỉnh (request ID, timing, metrics), cấu hình Celery, exception handler tập trung, và Celery Beat schedule cho các task định kỳ.

---

## 5. Celery — Tác vụ nền và lập lịch

Hệ thống sử dụng Celery với Redis làm broker để xử lý các tác vụ nền quan trọng.

Tác vụ early warning chạy hằng đêm, phân tích dữ liệu sinh viên và tạo cảnh báo cho giảng viên. Tác vụ weekly report chạy hằng tuần, tổng hợp báo cáo pilot. Tác vụ celery health kiểm tra sức khỏe queue định kỳ. Tác vụ event completeness kiểm tra tính đầy đủ của events. Tác vụ event duplication kiểm tra và phát hiện events trùng lặp. Tác vụ data quality chạy kiểm tra chất lượng dữ liệu. Tác vụ enforce retention trong privacy module thực thi chính sách lưu trữ dữ liệu. Tác vụ check incident SLA kiểm tra SLA xử lý sự cố bảo mật.

---

## 6. Frontend — Chi tiết kiến trúc

### 6.1 Cấu trúc App Router

Frontend sử dụng Next.js 14 App Router với layout groups để tổ chức routing theo vai trò.

Root layout tại src/app/layout.tsx thiết lập font Inter, SkipLink cho accessibility, và Toaster cho thông báo toast.

Group (auth) chứa trang đăng nhập tại /login. Group (student) chứa layout riêng cho sinh viên với sidebar navigation, và các trang dashboard, assessment, pathway, task, privacy. Group (lecturer) chứa các trang overview, alerts, history dành cho giảng viên.

Trang root tại / tự động redirect người dùng dựa trên vai trò: giảng viên đến /overview, sinh viên đến /dashboard, chưa đăng nhập đến /login.

### 6.2 Routing chi tiết

Đường dẫn / là redirect tự động. Đường dẫn /login là trang đăng nhập. Đường dẫn /dashboard là trang chính của sinh viên hiển thị tổng quan tiến độ. Đường dẫn /assessment là trang làm bài đánh giá đầu vào. Đường dẫn /pathway là trang xem lộ trình học tập cá nhân. Đường dẫn /task là trang làm bài tập micro-task. Đường dẫn /privacy là trang quản lý quyền riêng tư cá nhân. Đường dẫn /overview là trang tổng quan lớp học cho giảng viên. Đường dẫn /alerts là trang cảnh báo cho giảng viên. Đường dẫn /history là trang lịch sử can thiệp.

### 6.3 Components

Shared components bao gồm sidebar cho navigation, mobile-header cho responsive, page-header cho tiêu đề trang, stat-card cho thẻ thống kê, error-state cho trạng thái lỗi, và skip-link cho accessibility.

UI components sử dụng Radix UI primitives bao gồm button, card, input, badge, progress bar, skeleton loading, và toast notification.

Privacy components bao gồm consent-modal cho popup yêu cầu đồng ý.

### 6.4 State Management

Zustand được sử dụng cho state management nhẹ và hiệu quả. Hook use-auth quản lý toàn bộ trạng thái xác thực bao gồm thông tin user, trạng thái loading, consent pending, và các action login, logout, fetchProfile, checkConsent. Hook use-toast quản lý hệ thống thông báo toast.

### 6.5 API Client

File lib/api.ts triển khai ApiClient class xử lý mọi API call. Client tự động gửi cookie credentials với mỗi request. Khi nhận response 401, client tự động thử refresh token. Nếu refresh thất bại, redirect về /login.

File lib/constants.ts định nghĩa API_URL từ biến môi trường NEXT_PUBLIC_API_URL hoặc mặc định http://localhost:8000/api.

Next.js config thiết lập rewrite rules để proxy /api/ requests đến backend, cho phép frontend gọi API qua relative path.

### 6.6 Security Headers

next.config.js cấu hình Content Security Policy chỉ cho phép kết nối đến API domain, X-Frame-Options DENY chống clickjacking, HSTS cho HTTPS, và các header bảo mật khác.

---

## 7. Luồng nghiệp vụ chính (End-to-End Flows)

### 7.1 Luồng đăng ký và onboarding

Sinh viên đăng ký tài khoản với thông tin cơ bản. Hệ thống yêu cầu sinh viên đọc và đồng ý điều khoản sử dụng (consent). ConsentGateMiddleware chặn mọi truy cập PII cho đến khi consent được cấp. Sau khi đồng ý, sinh viên có thể truy cập đầy đủ hệ thống.

### 7.2 Luồng đánh giá đầu vào

Sinh viên xem danh sách bài đánh giá khả dụng. Sinh viên bắt đầu phiên đánh giá, hệ thống tạo AssessmentSession. Sinh viên lần lượt trả lời từng câu hỏi, mỗi câu trả lời được ghi lại là AssessmentResponse. Khi hoàn thành, hệ thống chấm điểm toàn bộ, tạo LearnerProfile phân tích điểm mạnh và điểm yếu theo từng concept. Từ kết quả đánh giá, hệ thống seed mastery state ban đầu cho từng concept, khởi tạo giá trị p_mastery trong BKT.

### 7.3 Luồng học thích ứng

Dựa trên mastery hiện tại, hệ thống xác định concept hiện tại và task tiếp theo phù hợp qua endpoint next-task. Sinh viên làm task, nộp kết quả qua endpoint submit. BKT engine cập nhật p_mastery dựa trên kết quả. Pathway logic quyết định bước tiếp theo: bổ sung nội dung nếu mastery thấp, tiếp tục nếu mastery trung bình, hoặc advance sang concept mới nếu mastery cao. Nếu mastery thấp, hệ thống tự động tạo ContentIntervention đề xuất tài liệu bổ sung từ SupplementaryContent. Toàn bộ quá trình được ghi lại qua EventLog.

### 7.4 Luồng cảnh báo sớm và can thiệp giảng viên

Celery task chạy hằng đêm quét dữ liệu tất cả sinh viên. Thuật toán early warning phát hiện các dấu hiệu bất thường và tạo Alert với mức severity RED hoặc YELLOW. Giảng viên mở dashboard, thấy overview lớp học với thống kê tổng hợp. Giảng viên xem danh sách alerts, có thể dismiss hoặc tạo InterventionAction. Giảng viên có thể tạo PathwayOverride để điều chỉnh lộ trình sinh viên cụ thể. Giảng viên theo dõi kết quả can thiệp qua lịch sử và follow-up.

### 7.5 Luồng wellbeing

Khi sinh viên học liên tục vượt ngưỡng 50 phút, frontend gọi wellbeing check. Hệ thống tạo WellbeingNudge nhắc sinh viên nghỉ ngơi. Sinh viên phản hồi nudge (tiếp tục hoặc nghỉ).

---

## 8. Bảo mật và quyền riêng tư

### 8.1 Mã hóa dữ liệu cá nhân

Dữ liệu nhạy cảm như mã sinh viên và số điện thoại được mã hóa bằng Fernet (symmetric encryption) trước khi lưu vào database. Khóa mã hóa PII_ENCRYPTION_KEY được quản lý riêng và bắt buộc trong production. Trường student_id_hash lưu hash một chiều để hỗ trợ tìm kiếm nhanh mà không cần giải mã toàn bộ.

### 8.2 Xác thực và phân quyền

JWT token được lưu trong httpOnly cookie, JavaScript phía client không thể đọc, chống tấn công XSS. Refresh token rotation đảm bảo token cũ bị vô hiệu khi token mới được tạo. Refresh token blacklist ngăn tái sử dụng token đã đăng xuất. Rate limiting bảo vệ các endpoint nhạy cảm như login, register, assessment submit, và export.

Ma trận RBAC đảm bảo sinh viên chỉ truy cập dữ liệu của mình, giảng viên chỉ truy cập dữ liệu sinh viên trong lớp được phân công, và admin có quyền truy cập rộng hơn. Truy cập cross-class hoặc cross-user được phân loại là lỗi P0 nghiêm trọng nhất.

### 8.3 Audit và tuân thủ

AuditMiddleware tự động ghi log mọi truy cập vào đường dẫn nhạy cảm. Log filter PII scrub loại bỏ thông tin cá nhân khỏi logs. Sentry production cấu hình send_default_pii=False và before_send redact để chắc chắn không gửi PII lên cloud. API docs trong production chỉ admin mới truy cập được.

### 8.4 Quy trình xử lý sự cố

Hệ thống có quy trình xử lý sự cố bảo mật dữ liệu với SLA 48 giờ. Quy trình gồm sáu bước: cô lập, đánh giá, thông báo, khắc phục, ghi nhận, và rà soát. Celery task tự động kiểm tra SLA sự cố định kỳ.

### 8.5 Security headers

Content Security Policy giới hạn nguồn tài nguyên được phép tải. X-Frame-Options DENY chống clickjacking. HSTS enforce kết nối HTTPS. Các header bảo mật bổ sung khác.

---

## 9. Hệ thống kiểm thử

### 9.1 Kim tự tháp kiểm thử 9 lớp

PALP áp dụng chiến lược kiểm thử toàn diện với 9 lớp từ thấp đến cao.

Lớp 1 là Unit test, kiểm tra từng hàm, method riêng lẻ. Lớp 2 là Component test, kiểm tra React components. Lớp 3 là Integration test, kiểm tra tương tác giữa các module. Lớp 4 là Contract test, kiểm tra API contract không bị breaking changes. Lớp 5 là End-to-End test, kiểm tra luồng nghiệp vụ hoàn chỉnh từ UI đến database. Lớp 6 là Data QA test, kiểm tra chất lượng và tính nhất quán dữ liệu. Lớp 7 là Security test, kiểm tra bảo mật và phân quyền. Lớp 8 là Recovery test, kiểm tra khả năng phục hồi hệ thống. Lớp 9 là Load test, kiểm tra hiệu năng dưới tải.

### 9.2 Công cụ và coverage

Backend sử dụng pytest với DJANGO_SETTINGS_MODULE=palp.settings.test, yêu cầu coverage tổng từ 80% trở lên, core modules từ 90% trở lên, các module adaptive, assessment, dashboard, accounts từ 85% trở lên.

Frontend sử dụng Vitest cho component và hook tests, Playwright cho E2E tests, và MSW (Mock Service Worker) cho mock API.

Contract testing sử dụng oasdiff để so sánh OpenAPI schema hiện tại với baseline, phát hiện breaking changes tự động trong CI.

### 9.3 Test markers

Backend tests được phân loại bằng pytest markers: integration cho integration tests, contract cho contract tests, security cho security tests, load cho load tests, data_qa cho data quality tests, recovery cho recovery tests, và slow cho tests chạy lâu.

### 9.4 Bảy hành trình E2E cốt lõi

Hệ thống định nghĩa 7 core E2E journeys (J1 đến J7) phải pass trước khi release, bao gồm toàn bộ luồng từ đăng nhập, đánh giá, học thích ứng, dashboard giảng viên, đến quản lý quyền riêng tư.

---

## 10. CI/CD Pipeline

### 10.1 GitHub Actions Workflow

CI pipeline chạy tự động trên mỗi push và pull request, bao gồm nhiều giai đoạn.

Giai đoạn lint kiểm tra code style và chất lượng bao gồm Ruff cho Python linting, Bandit cho security scanning, Mypy cho type checking, ESLint cho JavaScript/TypeScript, và tsc cho TypeScript type checking.

Giai đoạn migration check đảm bảo không có migration thiếu. Giai đoạn OpenAPI diff kiểm tra breaking changes trong API contract bằng oasdiff. Giai đoạn security audit chạy pip-audit và npm audit kiểm tra dependency vulnerabilities.

Giai đoạn test chạy pytest theo từng nhóm marker riêng biệt và frontend tests. Giai đoạn build kiểm tra ứng dụng build thành công.

### 10.2 Release Gate

Script release_gate.py thực hiện kiểm tra cuối cùng trước khi release, đảm bảo tất cả tiêu chí trong release checklist R-01 đến R-20 được đáp ứng.

---

## 11. Tiêu chuẩn chất lượng

### 11.1 Sáu tầng chất lượng

PALP định nghĩa sáu tầng chất lượng không thể đánh đổi lẫn nhau. Tầng L1 là đúng chức năng, code hoạt động đúng. Tầng L2 là đúng sư phạm, logic học tập và BKT chính xác. Tầng L3 là toàn vẹn dữ liệu, dữ liệu nhất quán và chính xác. Tầng L4 là bảo mật và quyền riêng tư. Tầng L5 là vận hành, backup, monitoring, rollback hoạt động. Tầng L6 là đo lường được, events và KPIs instrumentated đầy đủ.

### 11.2 Năm luồng vàng (Golden Flows)

GF-01 đến GF-05 là năm luồng nghiệp vụ quan trọng nhất phải hoạt động hoàn hảo: đăng nhập và consent, đánh giá đầu vào và tạo profile, học thích ứng với BKT, dashboard cảnh báo sớm, và export/xóa dữ liệu.

### 11.3 Năm anti-patterns

AP-01 Dead-end là sinh viên bị mắc kẹt không có bước tiếp theo. AP-02 Unexplainable state là hệ thống ở trạng thái không giải thích được. AP-03 Lost state là mất dữ liệu trạng thái. AP-04 Double-count là đếm trùng trong thống kê. AP-05 False alerts là cảnh báo sai cho giảng viên.

### 11.4 Sáu failure modes sư phạm

LI-F01 là can thiệp sai concept. LI-F02 là tăng độ khó quá sớm. LI-F03 là cảnh báo sai hàng loạt. LI-F04 là không quay lại lộ trình chính sau bổ sung. LI-F05 là tiến độ bị thổi phồng. LI-F06 là cảnh báo không có lý do. Tất cả đều là lỗi safety nghiêm trọng.

### 11.5 Release checklist

20 tiêu chí R-01 đến R-20 phải tất cả đều pass mới được release: tests pass, coverage đạt, E2E pass, OpenAPI không breaking, security 15/15, privacy 8/8, data QA 12/12, BKT bounds hợp lệ, events đầy đủ, SLA đạt, backup/restore hoạt động, rollback khả thi, monitoring sẵn sàng, UAT đạt, consent hoạt động, seed data sẵn sàng, Docker build thành công.

### 11.6 Go/No-Go

10 tiêu chí Go (G-01 đến G-10) phải đạt và 8 tiêu chí No-Go (NG-01 đến NG-08), bất kỳ cái nào vi phạm thì không được phép release. Các tiêu chí No-Go bao gồm logic adaptive sai, tiến độ hiển thị sai, phân quyền RBAC bị rò rỉ, export/delete không hoạt động, ETL thất bại âm thầm, events cốt lõi thiếu, backup/restore hỏng, và rollback không khả thi.

---

## 12. Definition of Done

Mỗi ticket phải đạt 12 tiêu chí D1 đến D12 trước khi được coi là hoàn thành: code review, unit tests, integration tests, negative tests, analytics events, audit logging khi cần, UI states đầy đủ, accessibility, monitoring, documentation, PO sign-off, và QA sign-off.

Pull Request template trên GitHub mirror đầy đủ 12 tiêu chí này, buộc developer check off từng mục trước khi merge.

---

## 13. UAT (User Acceptance Testing)

Kịch bản UAT được thiết kế cho 2 vòng testing trên môi trường staging.

Sinh viên thực hiện 8 tasks (S1 đến S8) bao gồm đăng nhập, làm đánh giá, xem lộ trình, làm bài tập, xem tiến độ, nhận nudge wellbeing, xem và quản lý quyền riêng tư, và xuất dữ liệu.

Giảng viên thực hiện 7 tasks (L1 đến L7) bao gồm đăng nhập, xem overview lớp, xem alerts, tạo can thiệp, xem mastery sinh viên, xem lịch sử, và xuất dữ liệu lớp.

Ngưỡng đạt bao gồm SUS score từ 80 trở lên, tỷ lệ hoàn thành task thành công, và điểm tin cậy từ người dùng.

---

## 14. Quy hoạch Sprint

Dự án được chia thành 10 sprint (W1 đến W10) với các cột mốc quyết định.

Tuần 4 (W4) là mốc baseline, đánh giá hệ thống cơ bản hoạt động ổn định. Tuần 10 (W10) là mốc pilot KPIs, đánh giá hiệu quả thực tế. Tuần 16 (W16) là mốc go/no-go cho phase 2, quyết định mở rộng hay không.

Ma trận RACI xác định rõ vai trò và trách nhiệm. Risk register theo dõi các rủi ro dự án. Success criteria được định nghĩa rõ ràng cho từng sprint.

---

## 15. Tóm tắt

PALP là một hệ thống EdTech toàn diện kết hợp công nghệ hiện đại với phương pháp sư phạm khoa học. Hệ thống cá nhân hóa trải nghiệm học tập thông qua BKT, cung cấp công cụ cảnh báo sớm cho giảng viên, đảm bảo quyền riêng tư dữ liệu nghiêm ngặt, và có hệ thống đo lường hiệu quả rõ ràng.

Với 9 Django apps, hơn 30 database models, hơn 50 API endpoints, 9 lớp kiểm thử, 20 tiêu chí release, và quy trình Go/No-Go nghiêm ngặt, PALP thể hiện cách tiếp cận kỹ thuật chuyên nghiệp cho một sản phẩm EdTech có trách nhiệm.

Điểm đặc biệt của PALP so với các nền tảng học tập khác là sự kết hợp giữa cá nhân hóa thích ứng thực sự (không chỉ gợi ý nội dung) với tính minh bạch (giải thích được mọi quyết định), tôn trọng quyền riêng tư (mã hóa PII, consent rõ ràng, quyền xóa dữ liệu), và vai trò trung tâm của giảng viên (human-in-the-loop, override pathway, can thiệp chủ động).
