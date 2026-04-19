# Motivation Design — SDT Principles & Anti-Gamification

> Tài liệu **bắt buộc đọc** cho mọi designer/dev/PM trước khi đề xuất bất kỳ feature liên quan đến tương tác sinh viên. Quy tắc trong tài liệu này là **hard rule**, không phải guideline.

## 1. Nguyên tắc tối thượng

**PALP TUYỆT ĐỐI không gamify hệ thống bằng extrinsic reward (points, badges, leaderboard, streak).**

Lý do khoa học: extrinsic rewards crowd-out intrinsic motivation đối với task có ý nghĩa nội tại như học tập. Đây là kết luận meta-analysis 128 experiments của [Deci, Koestner & Ryan 1999](https://psycnet.apa.org/record/1999-11174-001) "A meta-analytic review of experiments examining the effects of extrinsic rewards on intrinsic motivation" (Psychological Bulletin, 125(6)).

Hệ quả: sinh viên ban đầu được "câu" bằng badge/streak sẽ giảm động lực học khi reward dừng hoặc khi reward không còn hấp dẫn — và **không bao giờ phục hồi** về intrinsic level ban đầu. Điều này đặc biệt nguy hiểm với target audience của PALP (sinh viên mất định hướng, năng lực thấp) vì họ vốn đã intrinsic-motivation thấp.

## 2. Self-Determination Theory (SDT) — framework thay thế

Theo Deci & Ryan (2000, 2017) — [Ryan & Deci 2017 "Self-Determination Theory"](https://www.guilford.com/books/Self-Determination-Theory/Richard-Ryan-Edward-Deci/9781462528769) — con người có 3 nhu cầu tâm lý cơ bản. PALP phải support cả 3, không thay thế bằng extrinsic.

### 2.1 Autonomy — Cảm giác tự chủ

| Phải có | Không được có |
|---|---|
| Choice in pathway (chọn concept order khi có thể) | Forced single linear path |
| Opt-out mọi feature có thể (peer, coach cloud, affect) | Mandatory engagement với feature non-essential |
| "Bạn có thể bỏ qua bài này" option | "Bạn PHẢI hoàn thành để mở khoá" |
| Personal Frontier mode (P3) là default | So sánh peer mặc định bật |
| Sinh viên control retention/deletion data của mình | Hệ thống lock data |

### 2.2 Competence — Cảm giác có năng lực

| Phải có | Không được có |
|---|---|
| Mastery framing ("Bạn đã thông thạo 7/10 concept") | Score framing ("Bạn được 70/100 điểm") |
| Progress visualization vs past-self | Leaderboard vs other students |
| Difficulty tuning sao cho ZPD (vừa sức + 1 chút thử thách) | Difficulty fixed cho tất cả |
| Counterfactual explanation ("nếu bạn focus thêm 30%, mastery sẽ tăng X") (P6A XAI) | Black-box "Bạn không đủ tốt" |
| Coach giải thích sai sót cụ thể | Generic "Sai rồi, thử lại" |

### 2.3 Relatedness — Cảm giác kết nối

| Phải có | Không được có |
|---|---|
| Optional peer connection (reciprocal teaching opt-in) | Mandatory social comparison |
| Coach memory ("nhớ" sv là ai) | Anonymous interaction |
| Lecturer human touch (Instructor Co-pilot draft, lecturer approve) | Pure AI replacement |
| Buddy match là role-model (+0.5σ → +1σ), không phải competition | Rank against peers |
| Emergency contact opt-in cho moment khó khăn | Cô lập khi crisis |

## 3. Code review checklist — anti-gamification

Reviewer **bắt buộc** từ chối PR nếu code chứa bất kỳ điều sau:

- [ ] Field/UI hiển thị "score", "points", "XP" cho student-facing context
  - Exception: lecturer-facing analytics có thể có numeric score (vì context khác)
- [ ] Badge/achievement/medal/trophy icon hoặc model
- [ ] "Streak" counter (consecutive days/items)
- [ ] Leaderboard hoặc ranking giữa students (kể cả "top 10")
- [ ] Progress bar có "level up" animation/celebration
- [ ] Notification/nudge có ngôn ngữ "kiếm thêm X điểm"
- [ ] Compare absolute (sv A: 80, sv B: 75) thay vì relative percentile cohort cùng năng lực
- [ ] Loss aversion mechanic ("Đừng mất streak!")
- [ ] FOMO-inducing copy ("X bạn đã hoàn thành — bạn đang chậm")

Allowed (vì là information, không phải reward):
- ✅ Mastery percentage framing ("75% concept đã mastery")
- ✅ Progress vs past-self chart
- ✅ Counterfactual prediction ("focus +30% → risk -27 points")
- ✅ Personal goal completion ("Bạn đã hoàn thành 3/5 weekly goals đặt ra")

## 4. Copywriting guideline

| Tone tránh | Tone khuyến khích |
|---|---|
| "Bạn còn yếu hơn 65% bạn cùng lớp" (so sánh tiêu cực) | "Trong nhóm 25 bạn cùng xuất phát điểm, bạn đang ở khoảng giữa, có dư địa cải thiện ở concept X" |
| "Học ngay để không tụt lại!" (FOMO) | "Bạn đặt mục tiêu học X phút tuần này, hôm nay là cơ hội tốt để hoàn thành" |
| "Streak 7 ngày — đừng mất!" | "Bạn đã duy trì học 7 ngày liên tiếp. Tuần tới muốn đặt mục tiêu thế nào?" |
| "Hoàn thành để mở khoá level 3" | "Concept tiếp theo là Y, foundation tốt sẽ giúp bạn dễ tiếp thu hơn" |
| Generic "Sai rồi, làm lại" | "Coach thấy bạn đang vướng ở bước Z. Có vẻ liên quan đến concept Y — muốn xem giải thích không?" |

## 5. Use cases — apply SDT vào feature cụ thể

### 5.1 Risk Score hiển thị cho student (P1F)

**Sai (extrinsic comparison):**
> "Risk score của bạn: 72/100. Bạn nguy hiểm hơn 80% bạn cùng lớp."

**Đúng (SDT-aligned):**
> "Hệ thống nhận thấy bạn có một số tín hiệu cần chú ý: focus_minutes giảm tuần qua, hint usage cao ở concept X. Counterfactual: nếu bạn dành thêm 30 phút focus mỗi ngày, các tín hiệu này sẽ cải thiện đáng kể. Muốn coach giúp lên kế hoạch không?"

### 5.2 Peer Benchmark (P3C)

**Sai:**
> "Bảng xếp hạng tuần này: 1. Nguyễn A — 95đ, 2. Trần B — 88đ, ..., 23. Bạn — 45đ"

**Đúng:**
> "Trong cohort 25 bạn cùng xuất phát điểm với bạn, bạn đang ở khoảng giữa. Có 6 concept bạn đang thông thạo nhanh hơn trung bình cohort, 3 concept cần thêm thời gian. (Thông tin này ẩn danh, opt-in, có thể tắt trong settings.)"

### 5.3 Coach feedback sau task sai

**Sai:**
> "Sai rồi! -10 điểm. Streak bị reset. Thử lại để gỡ điểm."

**Đúng:**
> "Bạn đã thử cách giải này. Coach thấy bạn miss bước [Y]. Concept [Y] này thường khó vì lý do [Z]. Muốn xem worked example không, hay tự thử lại?"

### 5.4 Goal completion (P2C)

**Sai:**
> "Hoàn thành 3/5 goals → +50 XP, badge 'Goal Crusher'!"

**Đúng:**
> "Bạn đặt 5 mục tiêu tuần này, hoàn thành 3. Reflection: mục tiêu nào khó nhất? Tuần sau muốn đặt mục tiêu thế nào — giữ nguyên độ thử thách hay điều chỉnh?"

## 6. A/B test policy

Khi P0 causal framework hoạt động, mọi đề xuất "thêm 1 chút gamification element nhẹ" phải qua A/B test với các metrics:
- Short-term: engagement (click, time-on-task)
- **Long-term**: retention 30/60/90 ngày, intrinsic motivation survey (IMI scale)

Nếu short-term up nhưng long-term retention/IMI down → reject. Đây là pattern điển hình của extrinsic crowding-out — short-term win, long-term loss.

## 7. Exception cases

3 cases có thể dùng quantitative reward (đã review với learning scientist):

1. **Mastery acknowledgment**: hiện "Bạn đã thông thạo concept X" sau khi đạt threshold — đây là **competence feedback**, không phải reward, framing phải là "thông tin" không phải "phần thưởng".

2. **Streak chỉ trong reflection cycle**: hiện "Bạn đã reflection 4 tuần liên tiếp" trong UI reflection — đây support meta-cognitive practice, không phải compete.

3. **Lecturer-facing analytics**: dashboard cho lecturer có thể hiển thị score/rank vì context khác (lecturer cần triage, không phải bị motivate).

Mọi exception khác phải đi qua design review với learning scientist trong team trước khi implement.

## 8. Documentation linking

- Theory background: [LEARNING_SCIENCE_FOUNDATIONS.md](LEARNING_SCIENCE_FOUNDATIONS.md) section 2.3
- Code citation convention: [LEARNING_SCIENCE_FOUNDATIONS.md](LEARNING_SCIENCE_FOUNDATIONS.md) section 3
- PR review skill: [pr-review skill](../.ruler/skills/pr-review/SKILL.md)
- Frontend component skill: [frontend-component skill](../.ruler/skills/frontend-component/SKILL.md) — wraps SDT-aligned defaults

## 9. Living document

Khi có evidence mới (paper) hoặc field experience từ pilot, update guideline. Đề xuất quarterly review.
