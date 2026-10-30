# QA Kit – Agent test Android / iOS / Web bằng Claude Code

Bộ kit đóng gói một quy trình test dùng lại được cho mọi dự án:
**`/qc <project>`: làm một ca như QC engineer (check task tracker, ưu tiên, verify bug, test, update card + TC)**
hoặc **chọn project + platform + loại test → Claude chạy trên thiết bị/trình duyệt thật → xuất report, cập nhật Excel/Google Sheet, log bug lên Sheet/Jira/Trello/Mantis** (luôn có bước bạn duyệt trước khi ghi).

```
/qa shopx android functional module=MSG
```

---

## 0. Claude Desktop hay Terminal?

Dùng được **Claude Desktop**, nhưng phải dùng **tab Code** (chính là Claude Code chạy trong app desktop), không dùng tab Chat:

1. Mở Claude Desktop → tab **Code** → chọn thư mục `~/qa-kit`.
2. Chọn chạy **Local** (trên máy Mac), không chọn môi trường cloud/remote, vì điện thoại cắm USB vào Mac.
3. Gõ `/qa ...` như trong terminal. Tab Code đọc cùng `CLAUDE.md`, `.claude/skills/`, `.mcp.json` và `.claude/settings.json`.

Tab Chat của Claude Desktop **không** dùng được cho kit: nó không tự đọc skill trong thư mục, không chạy script Python và không điều khiển được thiết bị.

Lưu ý:
- Phần cài đặt bên dưới vẫn làm bằng Terminal (một lần).
- Nếu trong tab Code không thấy lệnh `/qa` hoặc MCP `mobile`/`playwright`, mở Terminal, chạy `claude` trong `~/qa-kit` để kiểm tra. Nếu Terminal chạy được thì lỗi nằm ở cấu hình Desktop.

---

## 1. Cài đặt trên MacBook (một lần, ~1–2 giờ)

```bash
# Công cụ nền (Xcode cài từ App Store trước)
brew install node python android-platform-tools
npm install -g @anthropic-ai/claude-code

# Giải nén kit vào ~/qa-kit
cd ~/qa-kit
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # rồi điền giá trị (mục 2, 3)
npx playwright install chromium   # chỉ cần nếu test web
git init && git add . && git commit -m "qa kit"   # .gitignore đã loại .env, secrets/, runs/
```

**Android (Xiaomi/HyperOS):** bật Developer options → *USB debugging*, *Install via USB*, *USB debugging (Security settings)*. Cắm máy, chạy `adb devices` và chọn Allow trên điện thoại.

**iPhone:** bật Developer Mode (Settings → Privacy & Security), chọn Trust máy Mac, rồi làm theo README của repo `mobile-next/mobile-mcp` để ký WebDriverAgent bằng Apple ID trong Xcode.

**MCP:** đã khai báo sẵn trong `.mcp.json` (mobile-mcp + Playwright MCP). Lần đầu mở `claude` trong thư mục kit, Claude Code hỏi có cho dùng MCP của project không → chọn đồng ý. Gõ `/mcp` để xem trạng thái.

---

## 2. Google Sheet (cho project có `testcases.source: gsheet`)

1. Vào Google Cloud Console, tạo project, rồi bật **Google Sheets API** và **Google Drive API**.
2. Vào IAM → Service Accounts → tạo service account → Keys → Add key → JSON. Tải file về và lưu thành `secrets/google-sa.json`.
3. Mở Google Sheet test case → Share cho **email của service account** (dạng `xxx@xxx.iam.gserviceaccount.com`) với quyền **Editor**.
4. Trong `.env`: `GOOGLE_SERVICE_ACCOUNT_JSON=secrets/google-sa.json`.
5. Trong `profile.yaml`: `gsheet_id` là đoạn ID dài trong URL `docs.google.com/spreadsheets/d/<ID>/edit`.

Nếu project dùng Excel: `testcases.source: excel` và `excel_path: projects/<name>/docs/<file>.xlsx`. Khi script ghi, **file phải đang đóng**. Script tự lưu một bản backup vào thư mục run.

---

## 3. Bug tracker (chọn theo từng project trong `profile.yaml` → `bug_tracker.type`)

| type | Cần trong `.env` | Cần trong `profile.yaml` |
|---|---|---|
| `sheet` | (dùng chung sheet test case) | `sheet_name: Bugs` (tab tự tạo nếu chưa có) |
| `trello` | `TRELLO_KEY`, `TRELLO_TOKEN` (trello.com/power-ups/admin → API key → Token) | `board_id` (lấy từ URL board), `list_name` |
| `jira` | Cloud: `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN` · Server: `JIRA_PAT` | `project_key`, `deployment`, `issue_type` |
| `mantis` | `MANTIS_BASE_URL`, `MANTIS_TOKEN` (My Account → API Tokens) | `project_id`, `category` |
| `none` | | chỉ xuất report |

Trước khi tạo bug, script luôn **kiểm tra trùng** bằng cách so tiêu đề với các bug đang mở trên tracker. Bug nghi trùng sẽ không được tạo cho tới khi bạn quyết định.

---

## 4. Kiểm tra

```bash
.venv/bin/python scripts/check_setup.py --project shopx
```
Script kiểm tra package Python, `.env`, thiết bị (adb/Xcode), từng tab module trong sheet (header, cột status) và kết nối tracker. Script không in giá trị secret. Khi thấy "All good" là sẵn sàng.

---

## 5. Sử dụng hằng ngày

```bash
cd ~/qa-kit && claude          # hoặc mở tab Code trong Claude Desktop
```

| Mục đích | Lệnh |
|---|---|
| Sinh test case cho module | `/qa shopx android tc-gen module=LIVE kind=functional` |
| Functional theo sheet | `/qa shopx android functional module=MSG batch=10` |
| Chạy một khoảng ID | `/qa shopx ios functional ids=MSG_001..MSG_015` |
| System test | `/qa shopx all system build=1.4.2` |
| Integration chéo 2 máy | `/qa shopx all integration module=MSG` |
| UI/UX | `/qa shopx web uiux module=CART` |
| Regression bản mới | `/qa shopx android regression build=1.4.3 bugs=#45,#47` |
| UAT | `/qa shopx all uat` |
| Ad-hoc | `/qa shopx ios adhoc focus=livestream time=20` |
| Cập nhật sheet/push bug cho run cũ | `/qa shopx android report run=runs/shopx/2026-10-08_functional_android_MSG` |
| Thêm chỉ dẫn riêng cho lần chạy | `/qa shopx android adhoc focus=chat bỏ qua gửi file, chỉ test text + emoji` |

**Luồng một lần chạy:**
1. Đọc profile, notes của project và module.
2. Kiểm tra thiết bị.
3. Chạy test theo batch, mỗi TC xong là ghi ngay vào `results.csv`.
4. Viết `report.md` và liệt kê bug.
5. Push bug ngay khi tìm thấy nếu đầu buổi bạn đã đồng ý (tạo bug Trello là quyền đã duyệt sẵn). Không cần gõ lệnh.
6. Cập nhật sheet (chạy dry-run trước).

Mọi output nằm trong `runs/<project>/<ngày>_<loại>_<platform>_<module>/`:
- `results.csv`
- `bugs.json`
- `report.md`
- `evidence/`

**Quy tắc ghi sheet:**
- Chỉ ghi vào cột Status của đúng platform, cùng với Bug ID, Note và Date.
- Không ghi đè status người đã nhập. Riêng regression được ghi đè các ô đang là Failed/Pending.
- Note chỉ được nối thêm, có tiền tố `[Claude][android]`.

---

## 5b. Chế độ QC Engineer – `/qc`

Mỗi lần gọi `/qc <project> [thời lượng]`, agent làm một "ca" giống senior QC thật:

0. **Hỏi một lần ở đầu buổi, rồi chạy tới hết giờ:** trước khi tính giờ, agent tự kiểm tra thiết bị, build,
   môi trường, account, test data, quyền tracker/sheet, đọc trước mọi task, rồi gửi MỘT tin: việc bạn cần làm,
   tối đa 5 câu hỏi (kèm cách hiểu mặc định), plan, các quyền trên máy cần cấp ngay (thư mục, Remote Control,
   Chrome extension, browser pane, Trello, sheet, adb, xcrun, điều khiển màn hình, quyền macOS) và xin quyền ghi
   cho cả ca (tạo bug, cập nhật/comment card, chuyển trạng thái, reopen, sheet, thêm TC). Trả lời "go" là duyệt hết;
   muốn bỏ mục nào thì ghi kèm, ví dụ "go, không reopen".
   Bạn trả lời "go" thì bắt đầu tính giờ. Trong ca agent không hỏi, không chờ: chỗ chưa rõ thì test theo cách hiểu
   hợp lý và ghi câu hỏi vào báo cáo, task bị chặn thì chuyển việc, bước ghi chưa được duyệt thì để "Pending approval".
   Bug xác nhận xong (repro 2 lần, không trùng) là post card ngay, task xong là cập nhật card ngay. Không cần gõ
   "post B1 B2 B3" hay cú pháp nào.
   Hết task thì làm tiếp: regression quanh bug vừa fix, chạy lại TC fail/blocked, TC chưa chạy, exploratory,
   viết TC còn thiếu. Build mới thì smoke test trước.
1. **Standup:** đọc handover ca trước, kiểm tra thiết bị, lấy build đang test, kéo task QC từ tracker
   (`scripts/tasks.py pull`).
2. **Lập plan theo priority, vừa thời lượng** (gửi cùng tin đầu buổi). Thứ tự ưu tiên:
   - P0 (Blocker/Critical/Hotfix) trước tiên.
   - Task quá hạn hoặc đến hạn hôm nay.
   - P1 > P2 > P3.
   - Cùng priority thì verify bug trước, rồi regression, test feature, cuối cùng viết TC.
   - Task có label Blocked/Need info không đưa vào plan.
3. **Làm từng task:**
   - Đọc card đầy đủ (mô tả, comment fix của dev, file đính kèm, TC liên quan).
   - Nhận task: gán mình vào card và chuyển sang "QC In Progress".
   - **Verify bug:** tái hiện đúng bước cũ trên build mới, test xung quanh vùng fix. Kết quả là VERIFIED, REOPENED,
     bug mới (link về card gốc) hoặc NEED INFO.
   - **Test feature:** đọc acceptance criteria, map TC có sẵn, viết thêm TC còn thiếu, chạy functional (+ UI/UX,
     integration nếu cần), explore 10–15 phút, log bug link về card. Kết quả là PASSED hoặc FAILED.
   - **Viết TC:** theo skill tc-gen.
   - Comment kết quả theo mẫu (build, thiết bị, đã check gì, bug, TC), đính kèm evidence, chuyển list,
     cập nhật sheet test case.
**Thời lượng (`30m`, `1h`, `1h30m`...):** `h` = giờ, `m` = phút, tối đa 8h. Agent ghi giờ bắt đầu, deadline và mốc
wrap-up (chừa 10% thời lượng, 5–15 phút) vào `plan.md`, lập plan vừa thời lượng, kiểm tra giờ bằng `date` trước mỗi
task, báo tiến độ dạng "35/60m". Đến mốc wrap-up thì làm xong TC đang chạy, lưu phần dở dang để ca sau làm tiếp,
rồi viết báo cáo trước deadline. Thời gian chờ bạn trả lời không bị tính. Không ghi thời lượng thì giữ như cũ
(`shift_minutes` trong profile, mặc định 120 phút).

4. **Handover:** viết `runs/<p>/_shift/<ngày>/report.md` gồm task đã xong, bug verified/reopened/mới, tiến độ sheet,
   việc bị block và plan ngày mai.

```
/qc shopx                          # cả ca, mọi platform, 120 phút (mặc định cũ)
/qc zingmp3 1h                       # làm QC trong 1 giờ, hết giờ thì dừng và báo cáo
/qc zingmp3 30m                      # làm QC trong 30 phút
/qc shopx android 1h30m            # chỉ task cần Android, 90 phút
/qc shopx android minutes=60       # cách cũ, vẫn dùng được (60 phút)
/qc shopx only=verify_bug build=1.4.3
/qc shopx task=#45,#47             # chỉ làm các card này
/qc shopx resume                   # làm tiếp ca hôm nay
```

**Cấu hình trong `profile.yaml → workflow`:**
- `queues`: list/label (Trello), JQL (Jira) hoặc status (Mantis/sheet) nào là task cho QC, thuộc loại nào.
- `states`: chuyển card sang đâu khi bắt đầu, verified, reopened, passed, failed.
- `priority_map`: label/priority nào tương ứng P0–P3.
- `autonomy`:

| Mức | Agent tự làm | Agent hỏi bạn |
|---|---|---|
| `cautious` | không ghi gì | mọi lần ghi |
| `standard` (mặc định) | sau khi bạn duyệt plan: nhận task, comment, chuyển verified/passed, cập nhật sheet | reopen, tạo bug mới, thêm TC (hỏi sau mỗi task) |
| `full` | mọi thứ | không hỏi (bug nghi trùng vẫn không tự tạo) |

Agent không bao giờ xoá/archive card, sửa comment của người khác, hay đóng bug mà nó chưa verify.
Mọi lần ghi lên tracker đều được log vào `runs/<p>/_shift/<ngày>/actions.log`.

Sau khi sửa tên list/label cho đúng board, chạy kiểm tra:
```bash
.venv/bin/python scripts/tasks.py check --project shopx   # list/status trong workflow có tồn tại trên board không
.venv/bin/python scripts/tasks.py pull --project shopx    # xem thử queue + thứ tự ưu tiên, không ghi gì
```

**Tracker là Bugs sheet (không dùng Trello/Jira):** dev đổi cột Status của bug thành `Fixed`; agent lấy các dòng đó
để verify, rồi ghi Status (`Verified`/`Reopened`) và cột `QC Note`. Cấu hình
`queues: {verify_bug: {statuses: [Fixed]}}`, `states: {verified: Verified, reopened: Reopened, in_progress: Retesting}`.

---

## 6. Mở rộng

**Thêm project:** gõ `/new-project shopx`. Claude tạo `projects/shopx/` từ template, hỏi các thông tin còn thiếu, đọc danh sách tab trong sheet để đề xuất module, rồi chạy check_setup.

**Thêm module:** thêm một dòng vào `modules:` trong `profile.yaml`:
```yaml
- {id: CART, name: "Cart", sheet: "Cart", id_prefix: "CART_", priority: high}
```
Nếu chưa có tab trong sheet, chạy `tc-gen` cho module đó, script sẽ tự tạo tab.

**Thêm loại test:**
1. Tạo `.claude/skills/test-<tên>/SKILL.md`, copy khung từ một skill test có sẵn: mục tiêu, nguồn TC, các bước, cách ghi kết quả.
2. Thêm một dòng vào bảng type trong `.claude/skills/qa/SKILL.md`.

**Chú ý riêng** (tầng sau thắng tầng trước):

| Tầng | Vị trí |
|---|---|
| Chung mọi dự án | `CLAUDE.md` |
| Dự án | `projects/<p>/notes.md` |
| Module | `projects/<p>/modules/<ID>.md` |
| Lần chạy | Chữ ghi thêm ở cuối lệnh `/qa` |

**Đổi nơi lưu report:** sửa `testcases.source` (excel/gsheet) và `bug_tracker.type` trong profile. Không cần sửa skill hay script.

---

## 7. Cấu trúc

```
qa-kit/
├── CLAUDE.md                   luật chung (luôn được đọc)
├── .mcp.json                   mobile-mcp, Playwright MCP
├── .claude/settings.json       quyền: cho phép script/MCP, chặn đọc .env và secrets/
├── .claude/skills/
│   ├── qc/                     /qc: ca làm việc QC (standup → plan → task → handover)
│   ├── qc-verify-bug/  qc-test-task/   playbook verify bug, test feature
│   ├── qa/                     router /qa
│   ├── new-project/            /new-project
│   ├── platform-mobile/  platform-web/
│   ├── tc-gen/  test-functional/  test-system/  test-integration/
│   ├── test-uiux/  test-regression/  test-uat/  test-adhoc/
│   └── report/                 cập nhật sheet + push bug + mẫu report
├── scripts/
│   ├── read_testcases.py       sheet → CSV test case cần chạy
│   ├── update_results.py       results.csv → Excel/Google Sheet
│   ├── append_testcases.py     thêm TC mới (tc-gen) vào sheet
│   ├── push_bugs.py            bugs.json → Sheet/Trello/Jira/Mantis (+ kiểm trùng)
│   ├── tasks.py                queue QC: pull/show/update/check task trên tracker
│   ├── check_setup.py  get_account.py  new_project.py
│   └── lib/ (config.py, sheets.py, trackers.py)
├── projects/_template/  projects/<name>/
├── runs/   secrets/   .env
```

---

## 8. Lỗi thường gặp

| Lỗi | Cách xử lý |
|---|---|
| `is open in Excel` | Đóng file Excel rồi chạy lại. |
| `Cannot open Google Sheet` | Chưa share sheet cho email service account, hoặc chưa bật Sheets API. |
| `Header row with 'ID' not found` | Tên cột trong `profile.yaml → testcases.columns` phải khớp chính xác với header trong sheet. |
| `kept_existing` | Ô status đã có giá trị do người nhập nên không ghi đè (đây là thiết kế). Regression dùng `--overwrite failed`. |
| `not_found` | ID trong results không có trong sheet. Bình thường với các dòng `ADHOC_`/`SYS_`/`UI_`. |
| Dropdown hoặc Summary không tính dòng mới | Sau khi thêm TC, mở rộng vùng data validation và công thức COUNTIF trong sheet. |
| iOS thao tác lỗi WDA | Khởi động lại WebDriverAgent theo README của mobile-mcp. |
| Hết quota Pro nhanh | Giảm `batch=`, ưu tiên đọc accessibility tree, giới hạn screenshot (đặc biệt khi test UI/UX). |
